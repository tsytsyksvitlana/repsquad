import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useTitle } from "../hooks.js";
import { Logo, Segmented } from "../components/ui.jsx";

const MODES = [["login", "Вхід"], ["register", "Реєстрація"]];

export default function AuthPage() {
  useTitle("RepSquad — вхід");
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    setError("");
    try {
      if (mode === "login") await login(f.get("username"), f.get("password"));
      else await register(f.get("username"), f.get("password"), f.get("display_name"));
      navigate("/feed");
    } catch (ex) { setError(ex.message); }
  };

  return (
    <div className="auth">
      <div className="logo"><Logo size={34} /><span>RepSquad</span></div>
      <p className="tagline">Соціальна мережа для спортсменів: тренуйтеся, діліться прогресом, питайте поради</p>
      <div className="card">
        <div className="mb-md">
          <Segmented options={MODES} value={mode} onChange={(m) => { setMode(m); setError(""); }} />
        </div>
        <form onSubmit={submit} autoComplete="on" key={mode}>
          <label>Логін
            <input name="username" required minLength={3} maxLength={20} pattern="[A-Za-z0-9_]{3,20}" autoComplete="username" placeholder="latin_letters_123" />
          </label>
          {mode === "register" && (
            <label>Ім'я в профілі
              <input name="display_name" maxLength={40} placeholder="Як вас показувати" />
            </label>
          )}
          <label>Пароль
            <input name="password" type="password" required minLength={8} autoComplete={mode === "login" ? "current-password" : "new-password"} placeholder="Щонайменше 8 символів" />
          </label>
          <button className="btn primary block" type="submit">
            {mode === "login" ? "Увійти" : "Створити акаунт"}
          </button>
          <p className="form-error" role="alert">{error}</p>
        </form>
      </div>
      <p className="muted small center">Демо-акаунт: <b>olena_fit</b> / <b>demo12345</b></p>
    </div>
  );
}
