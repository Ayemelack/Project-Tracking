"""AI Project Employee: provider abstraction, streaming and briefing.

OpenAI is exercised through an injected fake client so these tests never make
real network calls and never need an API key. The real provider selection
(graceful fallback to the deterministic engine without a key) is covered here
as well.
"""

from decimal import Decimal

from app.core.config import settings
from app.schemas.schemas import AssistantReply, AssistantStreamEvent
from app.services.assistant_provider import (
    DeterministicProvider,
    FallbackProvider,
    OpenAIProvider,
    Provider,
    get_provider,
)
from app.services.assistant_tools import execute_tool
from tests.test_assistant import ask
from tests.test_expenses import add_estimate

BRIEFING_URL = "/api/v1/assistant/briefing"
STREAM_URL = "/api/v1/assistant/ask/stream"


# ---------------------------------------------------------------------------
# Fakes for the OpenAI Responses API
# ---------------------------------------------------------------------------


class FakeOutputText:
    type = "output_text"

    def __init__(self, text: str):
        self.text = text


class FakeMessage:
    type = "message"

    def __init__(self, text: str):
        self.content = [FakeOutputText(text)]


class FakeFunctionCall:
    type = "function_call"

    def __init__(self, name: str, arguments: str, call_id: str = "call_1"):
        self.name = name
        self.arguments = arguments
        self.call_id = call_id


class FakeResponse:
    def __init__(self, response_id: str, output):
        self.id = response_id
        self.output = output
        self.error = None
        self.incomplete_details = None


class FakeData:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeEvent:
    def __init__(self, type: str, data=None):
        self.type = type
        self.data = data


class FakeStream:
    def __init__(self, events):
        self._events = list(events)

    def __iter__(self):
        return iter(self._events)


class FakeResponsesResource:
    def __init__(self, parent):
        self._parent = parent

    def create(self, **kwargs):
        self._parent.calls.append(kwargs)
        item = self._parent.sequence.pop(0)
        if isinstance(item, list):
            return FakeStream(item) if kwargs.get("stream") else list(item)
        return item


class FakeOpenAIClient:
    def __init__(self, sequence):
        self.sequence = list(sequence)
        self.calls = []
        self.responses = FakeResponsesResource(self)

    def _create(self, kwargs):
        item = self.sequence.pop(0)
        if isinstance(item, list):
            return FakeStream(item)
        return item


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------


def test_get_provider_without_key_uses_deterministic(monkeypatch):
    from pydantic import SecretStr

    # Forced no-key path (independent of whatever backend/.env contains).
    monkeypatch.setattr(settings, "ASSISTANT_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr(""))
    provider = get_provider()
    assert isinstance(provider, DeterministicProvider)


def test_openai_provider_selected_when_key_present(monkeypatch):
    from pydantic import SecretStr

    monkeypatch.setattr(settings, "ASSISTANT_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr("sk-test-not-a-real-key"))
    try:
        provider = get_provider()
    finally:
        monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr(""))
    assert isinstance(provider, FallbackProvider)
    assert isinstance(provider.primary, OpenAIProvider)
    assert isinstance(provider.fallback, DeterministicProvider)


def test_deterministic_provider_stream_events(db_session):
    provider = DeterministicProvider()
    events = list(provider.stream_reply(db_session, require_user(db_session, "owner"), "How much funding has been received?"))
    assert events[0].type == "delta"
    assert events[-1].type == "done"
    assert events[-1].intent == "funding"
    assert "0.00" in events[-1].text


# ---------------------------------------------------------------------------
# Fallback: primary fails (quota/network) -> deterministic still answers
# ---------------------------------------------------------------------------


class ExplodingOpenAIProvider(OpenAIProvider):
    def reply(self, db, user, question):
        return AssistantReply(intent="error", reply="I could not reach my language service.")

    def stream_reply(self, db, user, question):
        yield AssistantStreamEvent(type="status", text="Let me consult the project records.")
        yield AssistantStreamEvent(type="error", text="I could not reach my language service.")


def test_fallback_answers_when_primary_errors(db_session):
    fallback = FallbackProvider(
        primary=ExplodingOpenAIProvider(client=FakeOpenAIClient([]), model="fake"),
        fallback=DeterministicProvider(),
    )
    events = list(fallback.stream_reply(db_session, require_user(db_session, "owner"), "How much funding has been received?"))
    assert events[-1].type == "done"
    assert events[-1].intent == "funding"
    assert "0.00" in events[-1].text
    assert not any(e.type == "error" for e in events)


def test_fallback_passthrough_when_primary_succeeds(db_session):
    called = {"fallback": False}

    class OkProvider(Provider):
        name = "ok"

        def reply(self, db, user, question):
            return AssistantReply(intent="answer", reply="From OpenAI.", references=[])

        def stream_reply(self, db, user, question):
            yield AssistantStreamEvent(type="delta", text="From OpenAI.")
            yield AssistantStreamEvent(
                type="done", intent="answer", text="From OpenAI.", references=[]
            )

    class CounterFallback(DeterministicProvider):
        def reply(self, db, user, question):
            called["fallback"] = True
            return super().reply(db, user, question)

        def stream_reply(self, db, user, question):
            called["fallback"] = True
            yield from super().stream_reply(db, user, question)

    fallback = FallbackProvider(primary=OkProvider(), fallback=CounterFallback())
    reply = fallback.reply(db_session, require_user(db_session, "owner"), "hi")
    events = list(fallback.stream_reply(db_session, require_user(db_session, "owner"), "hi"))
    assert reply.reply == "From OpenAI."
    assert events[-1].text == "From OpenAI."
    assert called["fallback"] is False


def test_deterministic_endpoint_still_works(client):
    body = ask(client, "How much funding has been received?")
    assert body["intent"] == "funding"


# ---------------------------------------------------------------------------
# OpenAI tool calling (fake client, no network)
# ---------------------------------------------------------------------------


def _openai_provider(sequence) -> tuple[OpenAIProvider, FakeOpenAIClient]:
    client = FakeOpenAIClient(sequence)
    provider = OpenAIProvider(client=client, model="fake-model")
    return provider, client


def test_openai_reply_calls_tool_then_answers(db_session):
    estimate = add_estimate(db_session, total=Decimal("2000000.00"), title="Site Building")
    owner = require_user(db_session, "owner")

    provider, client = _openai_provider(
        [
            FakeResponse("r1", [FakeFunctionCall("get_estimates", "{}", "call_1")]),
            FakeResponse("r2", [FakeMessage("The verified estimate total is 2,000,000.00.")]),
        ]
    )

    reply = provider.reply(db_session, owner, "What is the current project estimate?")

    assert reply.intent == "estimates"
    assert "2,000,000.00" in reply.reply
    assert any(ref.entity_type == "estimate" and ref.entity_id == estimate.id for ref in reply.references)
    # Continuation used the tool output and the previous response id.
    second = client.calls[1]
    assert second.get("previous_response_id") == "r1"
    assert second["input"][0]["type"] == "function_call_output"
    assert second["input"][0]["call_id"] == "call_1"
    assert "Site Building" in second["input"][0]["output"]


def test_openai_reply_honest_when_model_has_no_data(db_session):
    provider, client = _openai_provider(
        [
            FakeResponse("r1", [FakeMessage("I don't have enough verified project records to answer that.")])
        ]
    )
    reply = provider.reply(db_session, require_user(db_session, "owner"), "Who supplied the cement?")
    assert reply.intent == "answer"
    assert "enough verified project records" in reply.reply
    assert reply.references == []


def test_openai_reply_error_is_graceful(db_session):
    class ExplodingClient(FakeOpenAIClient):
        def _create(self, kwargs):
            raise RuntimeError("boom")

    provider = OpenAIProvider(client=ExplodingClient([]), model="fake-model")
    reply = provider.reply(db_session, require_user(db_session, "owner"), "Overview please")
    assert reply.intent == "error"
    assert "api_key" not in reply.reply.lower()
    assert "traceback" not in reply.reply.lower()


def test_openai_stream_yields_deltas_and_done(db_session):
    provider, client = _openai_provider(
        [
            [
                FakeEvent("response.output_text.delta", FakeData(delta="Good ")),
                FakeEvent("response.output_text.delta", FakeData(delta="morning.")),
                FakeEvent(
                    "response.completed",
                    FakeData(response=FakeResponse("r1", [FakeMessage("Good morning.")])),
                ),
            ]
        ]
    )
    events = list(provider.stream_reply(db_session, require_user(db_session, "owner"), "Hi"))
    types = [e.type for e in events]
    assert types[0] == "status"
    assert "delta" in types
    assert types[-1] == "done"
    assert events[-1].text == "Good morning."
    assert client.calls[-1].get("stream") is True


def test_openai_stream_tool_loop_emits_tool_and_references(db_session):
    estimate = add_estimate(db_session, total=Decimal("1000000.00"), title="Warehouse")
    provider, client = _openai_provider(
        [
            [
                FakeEvent(
                    "response.completed",
                    FakeData(response=FakeResponse("t1", [FakeFunctionCall("get_estimates", "{}", "c1")])),
                ),
            ],
            [
                FakeEvent("response.output_text.delta", FakeData(delta="One confirmed estimate.")),
                FakeEvent(
                    "response.completed",
                    FakeData(response=FakeResponse("t2", [FakeMessage("One confirmed estimate.")])),
                ),
            ],
        ]
    )
    events = list(provider.stream_reply(db_session, require_user(db_session, "owner"), "Any estimates?"))
    tools = [e.tool for e in events if e.type == "tool"]
    done = [e for e in events if e.type == "done"][0]
    assert tools == ["get_estimates"]
    assert done.intent == "estimates"
    assert any(ref.entity_id == estimate.id for ref in done.references)


def test_openai_stream_error_is_graceful(db_session):
    class ExplodingStream(FakeOpenAIClient):
        def _create(self, kwargs):
            def gen():
                yield FakeEvent("response.failed", FakeData(response=FakeResponse("x", [])))

            return FakeStream(gen())

    provider = OpenAIProvider(client=ExplodingStream([]), model="fake-model")
    events = list(provider.stream_reply(db_session, require_user(db_session, "owner"), "Hi"))
    assert events[-1].type == "error"


# ---------------------------------------------------------------------------
# Controlled tools
# ---------------------------------------------------------------------------


def test_tool_get_record_missing_honest(db_session):
    owner = require_user(db_session, "owner")
    result = execute_tool(
        db_session,
        owner,
        "get_record",
        '{"record_type": "estimate", "record_id": "00000000-0000-0000-0000-000000000000"}',
    )
    assert result.output["found"] is False
    assert result.references == []
    assert result.output["error"] == "No such record exists."


def test_tool_unknown_tool_honest(db_session):
    result = execute_tool(db_session, require_user(db_session, "owner"), "get_secrets", "{}")
    assert result.output["error"] == "Tool 'get_secrets' is not available."


def test_tool_rejects_bad_json(db_session):
    result = execute_tool(db_session, require_user(db_session, "owner"), "get_record", "not-json")
    assert "not valid JSON" in result.output["error"]


# ---------------------------------------------------------------------------
# Briefing (pre-chat context from live data)
# ---------------------------------------------------------------------------


def require_user(db_session, role, username="assistant_test"):
    from app.models.models import User
    from app.core.security import hash_password

    user = db_session.query(User).filter(User.username == username).first()
    if user is None:
        user = User(
            username=username,
            full_name="Test Assistant User",
            password_hash=hash_password("test-pass-123"),
            role=role,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def test_briefing_requires_auth(raw_client):
    response = raw_client.get(BRIEFING_URL)
    assert response.status_code == 401


def test_briefing_uses_session_identity(client, db_session):
    body = client.get(BRIEFING_URL)
    assert body.status_code == 200, body.text
    data = body.json()
    assert data["greeting"]
    assert data["project_name"] == "Test Project"
    assert data["suggestions"]


def test_briefing_attention_from_live_records(client, db_session):
    add_estimate(db_session)  # confirmed estimate, no funding -> honest funding attention item
    data = client.get(BRIEFING_URL).json()
    kinds = [item["kind"] for item in data["attention"]]
    assert "funding" in kinds


def test_briefing_no_attention_when_nothing_to_report(client):
    data = client.get(BRIEFING_URL).json()
    assert data["attention"] == []


def test_stream_endpoint_returns_sse(client):
    response = client.post(
        STREAM_URL,
        json={"question": "How much funding has been received?"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert 'data: {"type":"done"' in response.text


def test_stream_endpoint_requires_auth(raw_client):
    response = raw_client.post(STREAM_URL, json={"question": "Overview please"})
    assert response.status_code == 401