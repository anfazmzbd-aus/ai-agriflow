from __future__ import annotations

from agentos.models import ChatMessage, EchoModel, ModelRequest


async def test_echo_model_returns_last_message() -> None:
    """EchoModel should return the final user message."""
    model = EchoModel()
    request = ModelRequest(messages=[ChatMessage(role="user", content="recommend irrigation")])

    response = await model.complete(request)

    assert response.message.role == "assistant"
    assert response.message.content == "recommend irrigation"
