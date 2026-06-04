import { useState } from "react";

import {
  conversationLabel,
  listConversations,
  login,
  type Conversation,
} from "./api";

/** Operator console: log in, then list this tenant's conversations (RLS-scoped). */
export function AdminConsole() {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [error, setError] = useState<string | null>(null);

  const onLogin = async () => {
    setError(null);
    try {
      const t = await login(email, password);
      setToken(t);
      setConversations(await listConversations(t));
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  if (!token) {
    return (
      <div className="olivo-admin-login">
        <div className="card">
          <div className="olivo-brand">
            <div className="logo">🫒</div>
            <h1>Olivo Admin</h1>
            <p>Restaurant chat console</p>
          </div>
          {error && <p className="olivo-error">{error}</p>}
          <input
            placeholder="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            placeholder="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button onClick={onLogin}>Sign in</button>
        </div>
      </div>
    );
  }

  return (
    <div className="olivo-admin">
      <div className="olivo-topbar">
        <span className="logo">🫒</span>
        <h1>Olivo Admin</h1>
      </div>
      <div className="olivo-content">
        <h2>Conversations</h2>
        {conversations.length === 0 ? (
          <p className="olivo-empty">No conversations yet.</p>
        ) : (
          <ul className="olivo-conv-list">
            {conversations.map((c) => (
              <li key={c.id} className="olivo-conv-card">
                <span className="icon">💬</span>
                <span className="title">{conversationLabel(c)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
