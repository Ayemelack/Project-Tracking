from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ratelimit import rate_limiter
from app.models.models import User
from app.schemas.schemas import (
    AssistantAskRequest,
    AssistantBriefing,
    AssistantReply,
    AssistantStreamEvent,
)
from app.services import assistant_provider, assistant_service
from app.api.v1.dependencies import get_current_user

router = APIRouter()

ASSISTANT_USER_LIMIT = 20
ASSISTANT_WINDOW_SECONDS = 60
RATE_LIMITED_MESSAGE = "Too many requests. Please try again shortly."


def _enforce_assistant_limit(username: str) -> None:
    if not rate_limiter.allow(
        f"assistant:{username}", ASSISTANT_USER_LIMIT, ASSISTANT_WINDOW_SECONDS
    ):
        raise HTTPException(status_code=429, detail=RATE_LIMITED_MESSAGE)


def _sse(events):
    """Frame provider events as Server-Sent Events (media_type text/event-stream)."""
    for event in events:
        if not isinstance(event, AssistantStreamEvent):
            continue
        yield f"data: {event.model_dump_json()}\n\n"


@router.post("/ask", response_model=AssistantReply)
def ask_assistant(
    data: AssistantAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Answer a natural-language question about the recorded project data.

    The reply is produced by the configured AI provider (OpenAI by default).
    Every factual answer is grounded in the backend: the provider may only use
    the controlled read-only tools, and the authenticated user's session is
    passed through so authorization stays on the backend. The provider never
    receives or returns the API key.
    """
    _enforce_assistant_limit(current_user.username)
    return assistant_provider.reply(db, current_user, data.question)


@router.post("/ask/stream", response_class=StreamingResponse)
def ask_assistant_stream(
    data: AssistantAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Streaming variant of /ask via Server-Sent Events.

    Emits AssistantStreamEvent objects (status, tool, delta, done, error).
    Streams the provider's generated text where supported; never fakes
    streaming with artificial delays.
    """
    _enforce_assistant_limit(current_user.username)
    return StreamingResponse(
        _sse(assistant_provider.stream_reply(db, current_user, data.question)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/briefing", response_model=AssistantBriefing)
def assistant_briefing(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pre-chat context for the AI Project Employee.

    The greeting uses the authenticated user's name and the actual project
    record; attention items are computed from the live database. This is
    deterministic and never calls a language model.
    """
    return assistant_service.build_briefing(db, current_user)