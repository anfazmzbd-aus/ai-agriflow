from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Role-tagged chat message exchanged with a model."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Model invocation request."""

    messages: Sequence[ChatMessage]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Model invocation response."""

    message: ChatMessage
    metadata: dict[str, object] = field(default_factory=dict)


class EchoModel:
    """Deterministic model adapter for local tests and examples."""

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Return the last input message as an assistant response."""
        content = request.messages[-1].content if request.messages else ""
        return ModelResponse(message=ChatMessage(role="assistant", content=content))
