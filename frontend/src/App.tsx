import { useEffect, useState } from "react";

import AccessScreen from "./AccessScreen";
import { getAuthSession, loginAdmin, logoutAdmin } from "./api";
import CalendarView from "./CalendarView";
import ClientsView from "./ClientsView";
import TrackerView from "./TrackerView";

type AccessMode = "guest" | "admin" | null;
type View = "weekly" | "calendar" | "clients";

function App() {
  const [accessMode, setAccessMode] = useState<AccessMode>(null);
  const [view, setView] = useState<View>("weekly");
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    getAuthSession()
      .then(({ authenticated }) => {
        if (authenticated) setAccessMode("admin");
      })
      .catch(() => undefined)
      .finally(() => setCheckingSession(false));
  }, []);

  async function signIn(password: string) {
    await loginAdmin(password);
    setAccessMode("admin");
    setView("weekly");
  }

  async function leaveAccessMode() {
    if (accessMode === "admin") {
      try {
        await logoutAdmin();
      } finally {
        setAccessMode(null);
        setView("weekly");
      }
      return;
    }
    setAccessMode(null);
    setView("weekly");
  }

  if (checkingSession) {
    return <main className="access-screen"><p className="session-loading">Loading Task Tracker…</p></main>;
  }

  if (!accessMode) {
    return <AccessScreen onGuest={() => setAccessMode("guest")} onAdminLogin={signIn} />;
  }

  const isAdmin = accessMode === "admin";

  return (
    <div className="app-shell">
      <header className="brand-bar">
        <div className="brand-bar__inner">
          <button type="button" className="brand-mark" onClick={() => setView("weekly")}>
            <span className="brand-symbol" aria-hidden="true" />
            Task Tracker
          </button>
          <nav className="app-nav" aria-label="Main navigation">
            <button type="button" className={view === "weekly" ? "active" : ""} onClick={() => setView("weekly")}>Weekly</button>
            <button type="button" className={view === "calendar" ? "active" : ""} onClick={() => setView("calendar")}>Calendar</button>
            {isAdmin && <button type="button" className={view === "clients" ? "active" : ""} onClick={() => setView("clients")}>Clients</button>}
          </nav>
          <div className="access-context">
            <span>{isAdmin ? "Admin" : "Guest"}</span>
            <button type="button" onClick={() => void leaveAccessMode()}>
              {isAdmin ? "Log out" : "Change access"}
            </button>
          </div>
        </div>
      </header>

      <main className="app">
        {view === "weekly" && <TrackerView isAdmin={isAdmin} />}
        {view === "calendar" && <CalendarView />}
        {view === "clients" && isAdmin && <ClientsView />}
      </main>
    </div>
  );
}

export default App;
