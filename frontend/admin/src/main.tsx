import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AdminConsole } from "./AdminConsole";

const root = document.getElementById("olivo-admin-root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <AdminConsole />
    </StrictMode>,
  );
}
