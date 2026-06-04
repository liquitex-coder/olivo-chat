"""Chat reply generation. Provider is abstracted so the demo runs with zero cost
and live Claude calls stay behind an explicit, cost-gated swap."""
from app.chat.provider import (
    AnthropicChatProvider,
    ChatProvider,
    DemoChatProvider,
    get_chat_provider,
)
from app.chat.service import generate_reply

__all__ = [
    "AnthropicChatProvider",
    "ChatProvider",
    "DemoChatProvider",
    "generate_reply",
    "get_chat_provider",
]
