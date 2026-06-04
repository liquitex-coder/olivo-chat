import { useEffect, useState } from "react";

import { isSendable, listMessages, sendMessage, type Message } from "./api";

interface Props {
  token: string;
  conversationId: string;
  tenantName?: string;
}

/** Customer-facing chat widget for a restaurant tenant (e.g. Trattoria Olivo). */
export function EmbedWidget({ token, conversationId, tenantName }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMessages(token, conversationId)
      .then(setMessages)
      .catch((e: unknown) => setError(String(e)));
  }, [token, conversationId]);

  const onSend = async () => {
    if (!isSendable(draft)) return;
    try {
      const created = await sendMessage(token, conversationId, draft.trim());
      setMessages((prev) => [...prev, created]);
      setDraft("");
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  return (
    <div className="olivo-embed">
      <div className="olivo-header">
        <div className="olivo-avatar">🍝</div>
        <div>
          <div className="olivo-title">{tenantName ?? "Olivo Chat"}</div>
          <div className="olivo-status">Online · usually replies instantly</div>
        </div>
      </div>
      <div className="olivo-messages">
        {messages.map((m) => (
          <div key={m.id} className={`olivo-msg olivo-msg--${m.role}`}>
            <div className="bubble">{m.content}</div>
          </div>
        ))}
        {error && <p className="olivo-error">{error}</p>}
      </div>
      <div className="olivo-compose">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void onSend();
          }}
          placeholder="Ask about the menu, hours, booking…"
        />
        <button onClick={onSend} disabled={!isSendable(draft)}>
          Send
        </button>
      </div>
    </div>
  );
}
