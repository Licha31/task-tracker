import { useMemo, useState, type FormEvent } from "react";

import type {
  Company,
  CompanyPayload,
  PayrollFrequency,
  SalesTaxFrequency,
} from "./types";

type FormState = {
  name: string;
  ein: string;
  payrollEnabled: boolean;
  suiId: string;
  sitId: string;
  principalOwner: string;
  payrollFrequency: PayrollFrequency;
  payrollPlatform: string;
  nextPayDate: string;
  nextProcessDate: string;
  semiMonthlyDay1: string;
  semiMonthlyDay2: string;
  salesTaxEnabled: boolean;
  salesTaxFrequency: SalesTaxFrequency;
  salesTaxNextDueDate: string;
};

type Props = {
  company: Company | null;
  onCancel: () => void;
  onSave: (payload: CompanyPayload) => Promise<void>;
};

function ClientForm({ company, onCancel, onSave }: Props) {
  const initial = useMemo<FormState>(
    () => ({
      name: company?.name ?? "",
      ein: company?.ein ?? "",
      payrollEnabled: Boolean(company?.payroll),
      suiId: company?.payroll?.sui_id ?? "",
      sitId: company?.payroll?.sit_id ?? "",
      principalOwner: company?.payroll?.principal_owner ?? "",
      payrollFrequency: company?.payroll?.frequency ?? "weekly",
      payrollPlatform: company?.payroll?.payroll_platform ?? "",
      nextPayDate: company?.payroll?.next_pay_date ?? "",
      nextProcessDate: company?.payroll?.next_process_date ?? "",
      semiMonthlyDay1: company?.payroll?.semi_monthly_day_1?.toString() ?? "",
      semiMonthlyDay2: company?.payroll?.semi_monthly_day_2?.toString() ?? "",
      salesTaxEnabled: Boolean(company?.sales_tax),
      salesTaxFrequency: company?.sales_tax?.frequency ?? "monthly",
      salesTaxNextDueDate: company?.sales_tax?.next_due_date ?? "",
    }),
    [company],
  );

  const [form, setForm] = useState(initial);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const update = <K extends keyof FormState>(field: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");

    if (!form.name.trim() || !form.ein.trim()) {
      setError("Company name and EIN are required.");
      return;
    }

    if (
      form.payrollEnabled &&
      (!form.payrollPlatform.trim() || !form.nextPayDate || !form.nextProcessDate)
    ) {
      setError("Payroll platform, next pay date and next process date are required.");
      return;
    }

    if (form.payrollEnabled && form.payrollFrequency === "semi_monthly") {
      const day1 = Number(form.semiMonthlyDay1);
      const day2 = Number(form.semiMonthlyDay2);

      if (!form.semiMonthlyDay1 || !form.semiMonthlyDay2) {
        setError("Both semi-monthly pay days are required.");
        return;
      }

      if (day1 < 1 || day1 > 31 || day2 < 1 || day2 > 31 || day1 === day2) {
        setError("Semi-monthly pay days must be different values between 1 and 31.");
        return;
      }
    }

    if (form.salesTaxEnabled && !form.salesTaxNextDueDate) {
      setError("Sales Tax next due date is required.");
      return;
    }

    const payload: CompanyPayload = {
      name: form.name.trim(),
      ein: form.ein.trim(),
      payroll: form.payrollEnabled
        ? {
            sui_id: form.suiId.trim() || null,
            sit_id: form.sitId.trim() || null,
            principal_owner: form.principalOwner.trim() || null,
            frequency: form.payrollFrequency,
            payroll_platform: form.payrollPlatform.trim(),
            next_pay_date: form.nextPayDate,
            next_process_date: form.nextProcessDate,
            semi_monthly_day_1:
              form.payrollFrequency === "semi_monthly"
                ? Number(form.semiMonthlyDay1)
                : null,
            semi_monthly_day_2:
              form.payrollFrequency === "semi_monthly"
                ? Number(form.semiMonthlyDay2)
                : null,
          }
        : null,
      sales_tax: form.salesTaxEnabled
        ? {
            frequency: form.salesTaxFrequency,
            next_due_date: form.salesTaxNextDueDate,
          }
        : null,
    };

    try {
      setSaving(true);
      await onSave(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save client.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="form-shell">
      <header className="form-heading">
        <div>
          <h1>{company ? "Edit client" : "Add client"}</h1>
          <p>Configure the company and the services you track.</p>
        </div>
        <button type="button" className="button secondary" onClick={onCancel}>
          Cancel
        </button>
      </header>

      <form onSubmit={submit}>
        {error && <p className="form-error">{error}</p>}

        <fieldset>
          <legend>Company</legend>
          <div className="field-grid two-columns">
            <label>
              <span>Company name</span>
              <input
                value={form.name}
                onChange={(event) => update("name", event.target.value)}
                required
              />
            </label>
            <label>
              <span>EIN</span>
              <input
                value={form.ein}
                onChange={(event) => update("ein", event.target.value)}
                required
              />
            </label>
          </div>
        </fieldset>

        <fieldset>
          <div className="fieldset-title-row">
            <legend>Payroll</legend>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={form.payrollEnabled}
                onChange={(event) => update("payrollEnabled", event.target.checked)}
              />
              <span>Enabled</span>
            </label>
          </div>

          {form.payrollEnabled && (
            <div className="field-grid two-columns">
              <label>
                <span>SUI ID</span>
                <input value={form.suiId} onChange={(event) => update("suiId", event.target.value)} />
              </label>
              <label>
                <span>SIT ID</span>
                <input value={form.sitId} onChange={(event) => update("sitId", event.target.value)} />
              </label>
              <label>
                <span>Principal owner</span>
                <input
                  value={form.principalOwner}
                  onChange={(event) => update("principalOwner", event.target.value)}
                />
              </label>
              <label>
                <span>Payroll platform</span>
                <input
                  value={form.payrollPlatform}
                  onChange={(event) => update("payrollPlatform", event.target.value)}
                  required
                />
              </label>
              <label>
                <span>Frequency</span>
                <select
                  value={form.payrollFrequency}
                  onChange={(event) =>
                    update("payrollFrequency", event.target.value as PayrollFrequency)
                  }
                >
                  <option value="weekly">Weekly</option>
                  <option value="biweekly">Biweekly</option>
                  <option value="semi_monthly">Semi-monthly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </label>

              {form.payrollFrequency === "semi_monthly" && (
                <>
                  <label>
                    <span>First pay day</span>
                    <input
                      type="number"
                      min="1"
                      max="31"
                      value={form.semiMonthlyDay1}
                      onChange={(event) => update("semiMonthlyDay1", event.target.value)}
                      required
                    />
                  </label>
                  <label>
                    <span>Second pay day</span>
                    <input
                      type="number"
                      min="1"
                      max="31"
                      value={form.semiMonthlyDay2}
                      onChange={(event) => update("semiMonthlyDay2", event.target.value)}
                      required
                    />
                  </label>
                </>
              )}

              <label>
                <span>Next process date</span>
                <input
                  type="date"
                  value={form.nextProcessDate}
                  onChange={(event) => update("nextProcessDate", event.target.value)}
                  required
                />
              </label>
              <label>
                <span>Next pay date</span>
                <input
                  type="date"
                  value={form.nextPayDate}
                  onChange={(event) => update("nextPayDate", event.target.value)}
                  required
                />
              </label>
            </div>
          )}
        </fieldset>

        <fieldset>
          <div className="fieldset-title-row">
            <legend>Sales Tax</legend>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={form.salesTaxEnabled}
                onChange={(event) => update("salesTaxEnabled", event.target.checked)}
              />
              <span>Enabled</span>
            </label>
          </div>

          {form.salesTaxEnabled && (
            <div className="field-grid two-columns">
              <label>
                <span>Frequency</span>
                <select
                  value={form.salesTaxFrequency}
                  onChange={(event) =>
                    update("salesTaxFrequency", event.target.value as SalesTaxFrequency)
                  }
                >
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                </select>
              </label>
              <label>
                <span>Next due date</span>
                <input
                  type="date"
                  value={form.salesTaxNextDueDate}
                  onChange={(event) => update("salesTaxNextDueDate", event.target.value)}
                  required
                />
              </label>
            </div>
          )}
        </fieldset>

        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="button primary" disabled={saving}>
            {saving ? "Saving…" : "Save client"}
          </button>
        </div>
      </form>
    </section>
  );
}

export default ClientForm;
