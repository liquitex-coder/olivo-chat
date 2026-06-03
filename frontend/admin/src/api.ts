// Minimal API client for the admin console.

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export const apiBaseUrl = (): string =>
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const bearer = (token: string): string => `Bearer ${token}`;

/** Pure helper: display title with a fallback for untitled conversations. */
export const conversationLabel = (c: Conversation): string =>
  c.title && c.title.trim().length > 0 ? c.title : "(untitled)";

export async function login(email: string, password: string): Promise<string> {
  const resp = await fetch(`${apiBaseUrl()}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) throw new Error("Invalid credentials");
  const body = (await resp.json()) as { access_token: string };
  return body.access_token;
}

export async function listConversations(token: string): Promise<Conversation[]> {
  const resp = await fetch(`${apiBaseUrl()}/api/v1/conversations`, {
    headers: { Authorization: bearer(token) },
  });
  if (!resp.ok) throw new Error(`listConversations failed: ${resp.status}`);
  return (await resp.json()) as Conversation[];
}
