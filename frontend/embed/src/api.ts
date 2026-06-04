// Minimal API client for the embed widget. The base URL comes from the Vite
// env (VITE_API_BASE_URL); for the demo a dummy bearer token is configured.

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export const apiBaseUrl = (): string =>
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Build the Authorization header value for a bearer token. */
export const bearer = (token: string): string => `Bearer ${token}`;

/** Pure helper: a draft user message is non-empty after trimming. */
export const isSendable = (draft: string): boolean => draft.trim().length > 0;

async function authedFetch(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<Response> {
  return fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: bearer(token),
      ...(init.headers ?? {}),
    },
  });
}

export async function listMessages(
  token: string,
  conversationId: string,
): Promise<Message[]> {
  const resp = await authedFetch(
    `/api/v1/conversations/${conversationId}/messages`,
    token,
  );
  if (!resp.ok) throw new Error(`listMessages failed: ${resp.status}`);
  return (await resp.json()) as Message[];
}

export async function sendMessage(
  token: string,
  conversationId: string,
  content: string,
): Promise<Message> {
  const resp = await authedFetch(
    `/api/v1/conversations/${conversationId}/messages`,
    token,
    { method: "POST", body: JSON.stringify({ role: "user", content }) },
  );
  if (!resp.ok) throw new Error(`sendMessage failed: ${resp.status}`);
  return (await resp.json()) as Message;
}
