"""Chat providers behind a single interface.

The default is `DemoChatProvider`: deterministic, offline, **no cost** — right for a
sales demo on dummy data. `AnthropicChatProvider` wraps the real Claude SDK but is
**not** wired in by default; selecting it makes billable API calls, so it stays behind
an explicit, cost-approved swap (the SDK is imported lazily so startup needs no key).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ChatProvider(Protocol):
    async def reply(self, *, user_message: str, history: list[str]) -> str: ...


class DemoChatProvider:
    """Deterministic canned reply — no external calls, no charges."""

    async def reply(self, *, user_message: str, history: list[str]) -> str:
        turn = len([h for h in history if h])
        return (
            "Thanks for contacting Trattoria Olivo! (demo) "
            f"You said: {user_message.strip()}"
            + (f" — this is turn {turn}." if turn else "")
        )


class AnthropicChatProvider:
    """Wraps the Anthropic SDK. Live calls bill `ANTHROPIC_API_KEY` → cost-gated."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def reply(self, *, user_message: str, history: list[str]) -> str:
        from anthropic import AsyncAnthropic  # lazy: no key / no import cost at startup

        client = AsyncAnthropic(api_key=self._api_key)
        resp = await client.messages.create(
            model=self._model,
            max_tokens=512,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


def get_chat_provider() -> ChatProvider:
    """FastAPI dependency. Demo default = zero cost. Swapping in the Anthropic
    provider is gated on explicit cost approval (billable live calls)."""
    return DemoChatProvider()
