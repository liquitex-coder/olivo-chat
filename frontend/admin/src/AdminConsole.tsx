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
        <h1>Olivo Admin</h1>
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
    );
  }

  return (
    <div className="olivo-admin">
      <h1>Conversations</h1>
      <ul>
        {conversations.map((c) => (
          <li key={c.id}>{conversationLabel(c)}</li>
        ))}
      </ul>
    </div>
  );
}
