import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import { DraftProvider } from "./context/DraftContext.jsx";
import { ToastProvider } from "./context/ToastContext.jsx";
import { VideosProvider } from "./context/VideosContext.jsx";
import "./styles.css";

// Hash routing keeps the Python server simple: it only has to serve index.html and static assets.
createRoot(document.getElementById("root")).render(
  <HashRouter>
    <ToastProvider>
      <AuthProvider>
        <VideosProvider>
          <DraftProvider>
            <App />
          </DraftProvider>
        </VideosProvider>
      </AuthProvider>
    </ToastProvider>
  </HashRouter>,
);
