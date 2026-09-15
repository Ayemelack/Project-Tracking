"""AI Project Employee: provider abstraction.

The AI Project Employee is a dispatcher in front of interchangeable answer
providers:

    AI Project Employee
        -> Provider Abstraction (this module)
            -> FallbackProvider  (primary -> deterministic on failure)
                -> OpenAIProvider   (OpenAI Responses API, tool calling, streaming)
                -> DeterministicProvider (the original retrieval engine, always available)

Authorization stays in the backend: the authenticated ``User`` and the request
``Session`` are passed in with every call, and the providers only ever resolve
data through the controlled tools in :mod:`app.services.assistant_tools`.

Provider selection is configuration-driven (``ASSISTANT_PROVIDER``). If OpenAI
is selected but no API key is configured, the deterministic provider is used so
the application keeps working instead of crashing. If OpenAI is selected and a
key is configured but OpenAI cannot produce an answer (quota, network or server
failure), the deterministic provider answers instead of surfacing an error, so
the employee stays useful during outages.
"""

import logging
from typing import Iterator

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import User
from app.schemas.schemas import (
    AssistantReference,
    AssistantReply,
    AssistantStreamEvent,
)
from app.services import assistant_service
from app.services.assistant_tools import (
    execute_tool,
    resolve_project_name,
    TOOL_SPECS,
)

logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTIONS = """You are the AI Project Employee for the {project}.

You are a project employee, not a generic chatbot. You help this user understand
the verified project records kept in the project's tracking system.

Rules:
- Answer using verified project information only. When a question needs
  project facts (amounts, dates, counts, statuses, people or other recorded
  data), call the appropriate project-data tool and explain exactly what the
  backend returns.
- Never invent project information. Never fabricate estimates, funding,
  expenses, resources, schedule entries, suppliers, dates or anyone's name.
- If the backend returns no record or not enough verified information, say
  something equivalent to: "I don't have enough verified project records to
  answer that." Do not guess or fill gaps with assumptions.
- Respect the user's permissions. Only report information the user is allowed
  to see. If you lack a tool that could answer, say so honestly.
- Explain calculations the backend returns (for example totals or remaining
  balances) in plain language.
- Distinguish recorded facts from possible discrepancies, and phrase
  discrepancies neutrally (for example: "the records show a recorded
  discrepancy that requires review").
- Provide record references when the tool results identify specific records,
  so the user can inspect them.
- Never claim something is recorded when it is not.
- Be concise, professional and helpful. Use the currency amounts exactly as
  the tools return them."""

_USER_MESSAGE = lambda question: [
    {"role": "user", "content": [{"type": "input_text", "text": question}]}
]

_TOOL_INTENT_MAP = {
    "get_project_summary": "overview",
    "get_estimates": "estimates",
    "get_funding": "funding",
    "get_expenses": "expenses",
    "get_resources": "resources",
    "get_schedule": "schedule",
    "get_delays": "delays",
}


class ProviderError(Exception):
    """Raised when the provider cannot produce an answer without crashing the app."""


class Provider:
    """Provider interface: ``reply`` (complete) and ``stream_reply`` (SSE)."""

    name: str = "base"

    def reply(self, db: Session, user: User, question: str) -> AssistantReply:
        raise NotImplementedError

    def stream_reply(self, db: Session, user: User, question: str) -> Iterator[AssistantStreamEvent]:
        raise NotImplementedError


class DeterministicProvider(Provider):
    """The original retrieval engine: instant, database-grounded, no LLM."""

    name = "deterministic"

    def reply(self, db: Session, user: User, question: str) -> AssistantReply:
        return assistant_service.answer(db, question)

    def stream_reply(self, db: Session, user: User, question: str) -> Iterator[AssistantStreamEvent]:
        reply = self.reply(db, user, question)
        for part in reply.reply.splitlines():
            yield AssistantStreamEvent(type="delta", text=part + "\n")
        yield AssistantStreamEvent(type="done", intent=reply.intent, text=reply.reply, references=reply.references)


class FallbackProvider(Provider):
    """Run the primary provider; degrade to a fallback when it cannot answer.

    When the primary provider reports ``intent == "error"`` (for example an
    exhausted quota, network outage or transient server failure), the fallback
    provider answers instead so the employee keeps working on grounded records.
    """

    name = "fallback"

    def __init__(self, primary: Provider, fallback: Provider):
        self.primary = primary
        self.fallback = fallback

    def reply(self, db: Session, user: User, question: str) -> AssistantReply:
        reply = self.primary.reply(db, user, question)
        if reply.intent == "error":
            logger.info("AI employee: primary provider failed; using the deterministic engine.")
            return self.fallback.reply(db, user, question)
        return reply

    def stream_reply(
        self, db: Session, user: User, question: str
    ) -> Iterator[AssistantStreamEvent]:
        failed = False
        try:
            for event in self.primary.stream_reply(db, user, question):
                if event.type == "error":
                    failed = True
                    break
                yield event
        except Exception:  # noqa: BLE001 - guard the outer generator
            failed = True
        if failed:
            logger.info("AI employee: primary stream failed; using the deterministic engine.")
            yield from self.fallback.stream_reply(db, user, question)


def _response_function_calls(response) -> list[dict]:
    calls = []
    for item in response.output:
        if getattr(item, "type", None) == "function_call":
            calls.append(
                {
                    "call_id": item.call_id,
                    "name": item.name,
                    "arguments": item.arguments or "{}",
                }
            )
    return calls


def _response_text(response) -> str:
    parts = []
    for item in response.output:
        if getattr(item, "type", None) == "message":
            for content in item.content:
                if getattr(content, "type", None) == "output_text":
                    parts.append(content.text)
    return "".join(parts)


def _intent_from_tools(used_tools: list[str]) -> str:
    if not used_tools:
        return "answer"
    seen = {_TOOL_INTENT_MAP[t] for t in used_tools if t in _TOOL_INTENT_MAP}
    return next(iter(seen)) if len(seen) == 1 else "answer"


class OpenAIProvider(Provider):
    """OpenAI-driven provider.

    Uses the OpenAI Responses API with tool/function calling against the
    controlled backend tools. Supports real streaming of the generated text.

    The client is injected so tests can substitute a fake without network
    calls.
    """

    name = "openai"

    def __init__(
        self,
        *,
        client,
        model: str,
        tools: list | None = None,
        max_turns: int = 4,
        system_instructions_template: str | None = None,
    ):
        self.client = client
        self.model = model
        self.tools = tools if tools is not None else TOOL_SPECS
        self.max_turns = max_turns
        self._instructions_template = (
            system_instructions_template or _SYSTEM_INSTRUCTIONS
        )

    def _instructions_for(self, db: Session, user: User) -> str:
        project = resolve_project_name(db, user) or "Project Tracking"
        return self._instructions_template.format(project=project)

    # -- shared tool execution ------------------------------------------------

    def _execute_calls(
        self,
        db: Session,
        user: User,
        calls: list[dict],
        references: list[AssistantReference],
    ) -> list[dict]:
        outputs: list[dict] = []
        for call in calls:
            result = execute_tool(db, user, call["name"], call["arguments"])
            references.extend(result.references)
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call["call_id"],
                    "output": result.as_tool_output(),
                }
            )
        return outputs

    # -- complete (non-streaming) reply --------------------------------------

    def reply(self, db: Session, user: User, question: str) -> AssistantReply:
        instructions = self._instructions_for(db, user)
        current_input: list = _USER_MESSAGE(question)
        previous_response_id: str | None = None
        used_tools: list[str] = []
        references: list[AssistantReference] = []

        try:
            response = None
            for _ in range(self.max_turns):
                kwargs = {
                    "model": self.model,
                    "instructions": instructions,
                    "input": current_input,
                    "tools": self.tools,
                }
                if previous_response_id:
                    kwargs["previous_response_id"] = previous_response_id
                response = self.client.responses.create(**kwargs)

                calls = _response_function_calls(response)
                if not calls:
                    break
                used_tools.extend(call["name"] for call in calls)
                current_input = self._execute_calls(db, user, calls, references)
                previous_response_id = response.id
                response = None

            if response is None:
                raise ProviderError(
                    "I could not finish consulting the project records. Please try again."
                )
            text = _response_text(response).strip()
            if not text:
                raise ProviderError(
                    "I could not produce a usable answer from the project records."
                )
            return AssistantReply(
                intent=_intent_from_tools(used_tools),
                reply=text,
                references=references[:10],
            )
        except ProviderError as exc:
            return AssistantReply(intent="error", reply=str(exc))
        except Exception as exc:  # noqa: BLE001 - never surface internals
            logger.warning("AI employee (openai) reply failed: %s", type(exc).__name__)
            return AssistantReply(
                intent="error",
                reply=(
                    "I could not reach my language service just now. Please try again in "
                    "a moment."
                ),
            )

    # -- streaming reply ------------------------------------------------------

    def stream_reply(self, db: Session, user: User, question: str) -> Iterator[AssistantStreamEvent]:
        instructions = self._instructions_for(db, user)
        current_input: list = _USER_MESSAGE(question)
        previous_response_id: str | None = None
        used_tools: list[str] = []
        references: list[AssistantReference] = []

        yield AssistantStreamEvent(type="status", text="Let me consult the project records.")

        try:
            final_text = ""
            complete = False
            for _ in range(self.max_turns):
                kwargs = {
                    "model": self.model,
                    "instructions": instructions,
                    "input": current_input,
                    "tools": self.tools,
                    "stream": True,
                }
                if previous_response_id:
                    kwargs["previous_response_id"] = previous_response_id

                stream = self.client.responses.create(**kwargs)
                chunk_parts: list[str] = []
                completed_response = None
                for event in stream:
                    event_type = getattr(event, "type", None)
                    data = getattr(event, "data", None)
                    if event_type == "response.output_text.delta":
                        delta = getattr(data, "delta", None)
                        if delta:
                            chunk_parts.append(delta)
                            yield AssistantStreamEvent(type="delta", text=delta)
                    elif event_type in ("error", "response.failed"):
                        raise ProviderError(
                            "My language service could not generate a reply. Please try again."
                        )
                    elif event_type == "response.completed" and data is not None:
                        completed_response = data.response

                if completed_response is None:
                    raise ProviderError(
                        "My language service did not return a reply. Please try again."
                    )

                calls = _response_function_calls(completed_response)
                if not calls:
                    final_text = "".join(chunk_parts) or _response_text(completed_response)
                    complete = True
                    break

                used_tools.extend(call["name"] for call in calls)
                outputs = self._execute_calls(db, user, calls, references)
                for call in calls:
                    yield AssistantStreamEvent(type="tool", tool=call["name"])
                previous_response_id = completed_response.id
                current_input = outputs

            if not complete:
                raise ProviderError(
                    "I could not finish consulting the project records. Please try again."
                )

            final_text = final_text.strip()
            if not final_text:
                raise ProviderError(
                    "I could not produce a usable answer from the project records."
                )

            yield AssistantStreamEvent(
                type="done",
                intent=_intent_from_tools(used_tools),
                text=final_text,
                references=references[:10],
            )
        except ProviderError as exc:
            yield AssistantStreamEvent(type="error", text=str(exc))
        except Exception as exc:  # noqa: BLE001 - never surface internals
            logger.warning("AI employee (openai) stream failed: %s", type(exc).__name__)
            yield AssistantStreamEvent(
                type="error",
                text="I could not reach my language service just now. Please try again in a moment.",
            )


def get_provider() -> Provider:
    """Select the active provider from configuration.

    - "deterministic": the original retrieval engine.
    - "openai" without an API key: the deterministic engine (graceful
      degradation, no crash).
    - "openai" with an API key: the OpenAI provider wrapped in a fallback that
      switches to the deterministic engine whenever OpenAI cannot answer.
    """
    provider_kind = settings.ASSISTANT_PROVIDER
    if provider_kind != "openai":
        return DeterministicProvider()
    api_key = settings.openai_api_key
    if not api_key:
        return DeterministicProvider()
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    primary = OpenAIProvider(client=client, model=settings.OPENAI_MODEL)
    return FallbackProvider(primary=primary, fallback=DeterministicProvider())


def reply(db: Session, user: User, question: str) -> AssistantReply:
    return get_provider().reply(db, user, question)


def stream_reply(db: Session, user: User, question: str) -> Iterator[AssistantStreamEvent]:
    return get_provider().stream_reply(db, user, question)