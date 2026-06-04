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
    """Deterministic, offline canned replies — no external calls, no charges.

    Replies are keyword-routed to sound like a real restaurant concierge for the
    sales demo; still fully deterministic (same input → same output)."""

    _CANNED: tuple[tuple[tuple[str, ...], str], ...] = (
        (
            ("reserv", "book", "table", "seat"),
            "Of course! I'd be glad to reserve a table at Trattoria Olivo. "
            "For how many guests and what time would you like to join us?",
        ),
        (
            ("hour", "open", "close", "time"),
            "We're open Tuesday–Sunday: lunch 12:00–15:00 and dinner 18:00–23:00. "
            "We're closed on Mondays. Shall I book you a table?",
        ),
        (
            ("vegan", "gluten", "allerg", "vegetarian", "celiac"),
            "Absolutely — we serve gluten-free pasta and several vegan and "
            "vegetarian dishes. Please let our staff know of any allergies and "
            "the kitchen will take care of you.",
        ),
        (
            ("menu", "dish", "special", "wine", "recommend"),
            "Tonight's specials are tagliatelle al tartufo and osso buco alla "
            "milanese, paired beautifully with our house Chianti. Would you like "
            "the full menu?",
        ),
        (
            ("park", "location", "address", "where"),
            "You'll find us at 12 Via Olivo, with street parking nearby and a "
            "garage two minutes away. Looking forward to welcoming you!",
        ),
    )

    async def reply(self, *, user_message: str, history: list[str]) -> str:
        text = user_message.lower()
        for keywords, answer in self._CANNED:
            if any(k in text for k in keywords):
                return answer
        return (
            "Thanks for reaching out to Trattoria Olivo! I can help with "
            "reservations, opening hours, the menu, or dietary options — what "
            "would you like to know?"
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
