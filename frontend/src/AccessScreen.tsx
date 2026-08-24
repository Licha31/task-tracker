import { useState, type FormEvent } from "react";

type Props = {
  onGuest: () => void;
  onAdminLogin: (password: string) => Promise<void>;
};

function AccessScreen({ onGuest, onAdminLogin }: Props) {
  const [showLogin, setShowLogin] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await onAdminLogin(password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in.");
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="access-screen">
      <section className="access-panel" aria-labelledby="access-title">
        <p className="product-wordmark">
          <span className="brand-symbol" aria-hidden="true" />
          Task Tracker
        </p>
        <h1 id="access-title">Choose access</h1>

        {!showLogin ? (
          <div className="access-options">
            <button type="button" onClick={onGuest}>
              <span className="access-number">01</span>
              <span>
                <strong>Guest</strong>
                <small>View weekly and monthly operations</small>
              </span>
              <span aria-hidden="true">→</span>
            </button>
            <button type="button" onClick={() => setShowLogin(true)}>
              <span className="access-number">02</span>
              <span>
                <strong>Admin</strong>
                <small>Manage tracker</small>
              </span>
              <span aria-hidden="true">→</span>
            </button>
          </div>
        ) : (
          <form className="login-form" onSubmit={submit}>
            <label>
              <span>Admin password</span>
              <input
                type="password"
                autoComplete="current-password"
                autoFocus
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            {error && <p className="form-error">{error}</p>}
            <div className="login-actions">
              <button type="button" className="button secondary" onClick={() => setShowLogin(false)}>
                Back
              </button>
              <button type="submit" className="button primary" disabled={submitting}>
                {submitting ? "Signing in…" : "Sign in"}
              </button>
            </div>
          </form>
        )}
      </section>
    </main>
  );
}

export default AccessScreen;
