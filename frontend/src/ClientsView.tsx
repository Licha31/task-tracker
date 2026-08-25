import { useEffect, useState } from "react";

import { createClient, deleteClient, getClients, updateClient } from "./api";
import ClientForm from "./ClientForm";
import type { Company, CompanyPayload } from "./types";

type ClientView =
  | { type: "list" }
  | { type: "create" }
  | { type: "edit"; company: Company };

function formatFrequency(value: string) {
  return value.replace("semi_monthly", "semi-monthly").replaceAll("_", " ");
}

function ClientsView() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [view, setView] = useState<ClientView>({ type: "list" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadClients() {
    try {
      setLoading(true);
      setError("");
      setCompanies(await getClients());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load clients.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadClients();
  }, []);

  async function saveClient(payload: CompanyPayload) {
    if (view.type === "edit") {
      await updateClient(view.company.id, payload);
    } else {
      await createClient(payload);
    }

    await loadClients();
    setView({ type: "list" });
  }

  async function removeClient(company: Company) {
    if (!window.confirm(`Delete ${company.name}?`)) {
      return;
    }

    try {
      await deleteClient(company.id);
      await loadClients();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete client.");
    }
  }

  if (view.type !== "list") {
    return (
      <ClientForm
        company={view.type === "edit" ? view.company : null}
        onCancel={() => setView({ type: "list" })}
        onSave={saveClient}
      />
    );
  }

  return (
    <section className="clients-view">
      <header className="clients-header">
        <div>
          <h1>Clients</h1>
          <p>Payroll and Sales Tax setup.</p>
        </div>

        <button type="button" className="button primary" onClick={() => setView({ type: "create" })}>
          Add client
        </button>
      </header>

      {error && <p className="form-error">{error}</p>}

      {loading ? (
        <div className="empty-state">Loading clients…</div>
      ) : companies.length === 0 ? (
        <div className="empty-state">No clients yet.</div>
      ) : (
        <div className="clients-list">
          <div className="client-list-header" aria-hidden="true">
            <span>Company</span>
            <span>Services</span>
            <span>Payroll platform</span>
            <span>Frequency</span>
            <span>Actions</span>
          </div>
          {companies.map((company) => {
            const payrollCount = company.payroll_schedules.length;
            const salesTaxCount = company.sales_tax_registrations.length;
            const services = [
              payrollCount > 0 && `${payrollCount} Payroll`,
              salesTaxCount > 0 && `${salesTaxCount} Sales Tax`,
            ].filter(Boolean).join(" · ");

            return (
              <article className="client-row" key={company.id}>
                <div className="client-identity">
                  <h2>{company.name}</h2>
                  <p>EIN {company.ein}</p>
                </div>

                <div className="client-cell client-services">
                  <span className="client-cell-label">Services</span>
                  <strong>{services || "None"}</strong>
                </div>

                <div className="client-cell client-platform">
                  <span className="client-cell-label">Payroll platform</span>
                  <strong>
                    {[...new Set(company.payroll_schedules.map((item) => item.payroll_platform))]
                      .join(" · ") || "—"}
                  </strong>
                </div>

                <div className="client-cell client-frequency">
                  <span className="client-cell-label">Frequency</span>
                  {company.payroll_schedules.map((schedule) => (
                    <p key={`payroll-${schedule.id}`}>
                      <small>{schedule.jurisdiction}</small>{formatFrequency(schedule.frequency)}
                    </p>
                  ))}
                  {company.sales_tax_registrations.map((registration) => (
                    <p key={`sales-tax-${registration.id}`}>
                      <small>{registration.jurisdiction}</small>
                      {formatFrequency(registration.frequency)}
                    </p>
                  ))}
                  {payrollCount === 0 && salesTaxCount === 0 && <strong>—</strong>}
                </div>

                <div className="client-actions">
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => setView({ type: "edit", company })}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="button delete-action"
                    onClick={() => void removeClient(company)}
                  >
                    Delete
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default ClientsView;
