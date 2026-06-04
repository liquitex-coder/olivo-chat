import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { EmbedWidget } from "./EmbedWidget";
import "./styles.css";

// Demo wiring: a dummy tenant token + conversation id come from Vite env.
// For a real embed these would be issued per restaurant site.
const token = import.meta.env.VITE_DEMO_TOKEN ?? "demo-token";
const conversationId =
  import.meta.env.VITE_DEMO_CONVERSATION_ID ??
  "00000000-0000-0000-0000-000000000000";

const root = document.getElementById("olivo-embed-root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <EmbedWidget
        token={token}
        conversationId={conversationId}
        tenantName="Trattoria Olivo"
      />
    </StrictMode>,
  );
}
