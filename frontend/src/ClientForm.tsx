import { useMemo, useState, type FormEvent } from "react";

import type {
  Company,
  CompanyPayload,
  PayrollFrequency,
  PayrollScheduleInput,
  SalesTaxFrequency,
  SalesTaxRegistrationInput,
} from "./types";

type PayrollDraft = PayrollScheduleInput & { key: string };
type SalesTaxDraft = SalesTaxRegistrationInput & { key: string };

type FormState = {
  name: string;
  ein: string;
  payrollSchedules: PayrollDraft[];
  salesTaxRegistrations: SalesTaxDraft[];
};

type Props = {
  company: Company | null;
  onCancel: () => void;
  onSave: (payload: CompanyPayload) => Promise<void>;
};

let draftSequence = 0;

function draftKey(prefix: string) {
  draftSequence += 1;
  return `${prefix}-${draftSequence}`;
}

function emptyPayrollSchedule(): PayrollDraft {
  return {
    key: draftKey("payroll"),
    label: "",
    jurisdiction: "",
    sui_id: null,
    sit_id: null,
    principal_owner: null,
    frequency: "weekly",
    payroll_platform: "",
    next_pay_date: "",
    next_process_date: "",
    semi_monthly_day_1: null,
    semi_monthly_day_2: null,
  };
}

function emptySalesTaxRegistration(): SalesTaxDraft {
  return {
    key: draftKey("sales-tax"),
    jurisdiction: "",
    frequency: "monthly",
    next_due_date: "",
  };
}

function ClientForm({ company, onCancel, onSave }: Props) {
  const initial = useMemo<FormState>(
    () => ({
      name: company?.name ?? "",
      ein: company?.ein ?? "",
      payrollSchedules:
        company?.payroll_schedules.map((schedule) => ({
          ...schedule,
          key: draftKey("payroll"),
        })) ?? [],
      salesTaxRegistrations:
        company?.sales_tax_registrations.map((registration) => ({
          ...registration,
          key: draftKey("sales-tax"),
        })) ?? [],
    }),
    [company],
  );

  const [form, setForm] = useState(initial);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function updatePayroll(index: number, values: Partial<PayrollDraft>) {
    setForm((current) => ({
      ...current,
      payrollSchedules: current.payrollSchedules.map((schedule, scheduleIndex) =>
        scheduleIndex === index ? { ...schedule, ...values } : schedule,
      ),
    }));
  }

  function updateSalesTax(index: number, values: Partial<SalesTaxDraft>) {
    setForm((current) => ({
      ...current,
      salesTaxRegistrations: current.salesTaxRegistrations.map(
        (registration, registrationIndex) =>
          registrationIndex === index ? { ...registration, ...values } : registration,
      ),
    }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");

    if (!form.name.trim() || !form.ein.trim()) {
      setError("Company name and EIN are required.");
      return;
    }

    for (const schedule of form.payrollSchedules) {
      if (
        !schedule.label.trim()
        || !schedule.jurisdiction.trim()
        || !schedule.payroll_platform.trim()
        || !schedule.next_pay_date
        || !schedule.next_process_date
      ) {
        setError(
          "Each Payroll Schedule requires a label, jurisdiction, platform, process date and pay date.",
        );
        return;
      }
      if (
        schedule.frequency === "semi_monthly"
        && (
          schedule.semi_monthly_day_1 === null
          || schedule.semi_monthly_day_2 === null
          || schedule.semi_monthly_day_1 === schedule.semi_monthly_day_2
        )
      ) {
        setError("Semi-monthly pay days must be different values between 1 and 31.");
        return;
      }
    }

    if (
      form.salesTaxRegistrations.some(
        (registration) => !registration.jurisdiction.trim() || !registration.next_due_date,
      )
    ) {
      setError("Each Sales Tax Registration requires a jurisdiction and next due date.");
      return;
    }

    const payload: CompanyPayload = {
      name: form.name.trim(),
      ein: form.ein.trim(),
      payroll_schedules: form.payrollSchedules.map(({ key: _key, ...schedule }) => ({
        ...schedule,
        label: schedule.label.trim(),
        jurisdiction: schedule.jurisdiction.trim(),
        payroll_platform: schedule.payroll_platform.trim(),
        sui_id: schedule.sui_id?.trim() || null,
        sit_id: schedule.sit_id?.trim() || null,
        principal_owner: schedule.principal_owner?.trim() || null,
        semi_monthly_day_1:
          schedule.frequency === "semi_monthly" ? schedule.semi_monthly_day_1 : null,
        semi_monthly_day_2:
          schedule.frequency === "semi_monthly" ? schedule.semi_monthly_day_2 : null,
      })),
      sales_tax_registrations: form.salesTaxRegistrations.map(
        ({ key: _key, ...registration }) => ({
          ...registration,
          jurisdiction: registration.jurisdiction.trim(),
        }),
      ),
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
        <button type="button" className="button secondary" onClick={onCancel}>Cancel</button>
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
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
              />
            </label>
            <label>
              <span>EIN</span>
              <input
                value={form.ein}
                onChange={(event) => setForm({ ...form, ein: event.target.value })}
                required
              />
            </label>
          </div>
        </fieldset>

        <fieldset>
          <legend>Payroll Schedules</legend>
          <div className="fieldset-title-row">
            <p className="fieldset-description">Independent schedules by payroll group and jurisdiction.</p>
            <button
              type="button"
              className="button secondary"
              onClick={() => setForm((current) => ({
                ...current,
                payrollSchedules: [...current.payrollSchedules, emptyPayrollSchedule()],
              }))}
            >
              Add Payroll Schedule
            </button>
          </div>

          {form.payrollSchedules.length === 0 ? (
            <p className="configuration-empty">No Payroll Schedules configured.</p>
          ) : (
            <div className="configuration-list">
              {form.payrollSchedules.map((schedule, index) => (
                <section className="configuration-row" key={schedule.key}>
                  <header className="configuration-heading">
                    <div>
                      <span>Payroll {String(index + 1).padStart(2, "0")}</span>
                      <strong>{schedule.label || "New schedule"}</strong>
                    </div>
                    <button
                      type="button"
                      className="button delete-action"
                      onClick={() => setForm((current) => ({
                        ...current,
                        payrollSchedules: current.payrollSchedules.filter(
                          (_, scheduleIndex) => scheduleIndex !== index,
                        ),
                      }))}
                    >
                      {schedule.id ? "Archive" : "Remove"}
                    </button>
                  </header>
                  <div className="field-grid two-columns">
                    <label>
                      <span>Label</span>
                      <input
                        value={schedule.label}
                        onChange={(event) => updatePayroll(index, { label: event.target.value })}
                        placeholder="Employees"
                        required
                      />
                    </label>
                    <label>
                      <span>Jurisdiction</span>
                      <input
                        value={schedule.jurisdiction}
                        onChange={(event) => updatePayroll(index, { jurisdiction: event.target.value })}
                        placeholder="FL"
                        required
                      />
                    </label>
                    <label>
                      <span>Payroll platform</span>
                      <input
                        value={schedule.payroll_platform}
                        onChange={(event) => updatePayroll(index, { payroll_platform: event.target.value })}
                        required
                      />
                    </label>
                    <label>
                      <span>Frequency</span>
                      <select
                        value={schedule.frequency}
                        onChange={(event) => updatePayroll(index, {
                          frequency: event.target.value as PayrollFrequency,
                        })}
                      >
                        <option value="weekly">Weekly</option>
                        <option value="biweekly">Biweekly</option>
                        <option value="semi_monthly">Semi-monthly</option>
                        <option value="monthly">Monthly</option>
                      </select>
                    </label>
                    <label>
                      <span>SUI ID</span>
                      <input
                        value={schedule.sui_id ?? ""}
                        onChange={(event) => updatePayroll(index, { sui_id: event.target.value })}
                      />
                    </label>
                    <label>
                      <span>SIT ID</span>
                      <input
                        value={schedule.sit_id ?? ""}
                        onChange={(event) => updatePayroll(index, { sit_id: event.target.value })}
                      />
                    </label>
                    <label>
                      <span>Principal owner</span>
                      <input
                        value={schedule.principal_owner ?? ""}
                        onChange={(event) => updatePayroll(index, { principal_owner: event.target.value })}
                      />
                    </label>
                    {schedule.frequency === "semi_monthly" && (
                      <>
                        <label>
                          <span>First pay day</span>
                          <input
                            type="number"
                            min="1"
                            max="31"
                            value={schedule.semi_monthly_day_1 ?? ""}
                            onChange={(event) => updatePayroll(index, {
                              semi_monthly_day_1: event.target.value
                                ? Number(event.target.value)
                                : null,
                            })}
                            required
                          />
                        </label>
                        <label>
                          <span>Second pay day</span>
                          <input
                            type="number"
                            min="1"
                            max="31"
                            value={schedule.semi_monthly_day_2 ?? ""}
                            onChange={(event) => updatePayroll(index, {
                              semi_monthly_day_2: event.target.value
                                ? Number(event.target.value)
                                : null,
                            })}
                            required
                          />
                        </label>
                      </>
                    )}
                    <label>
                      <span>Next process date</span>
                      <input
                        type="date"
                        value={schedule.next_process_date}
                        onChange={(event) => updatePayroll(index, { next_process_date: event.target.value })}
                        required
                      />
                    </label>
                    <label>
                      <span>Next pay date</span>
                      <input
                        type="date"
                        value={schedule.next_pay_date}
                        onChange={(event) => updatePayroll(index, { next_pay_date: event.target.value })}
                        required
                      />
                    </label>
                  </div>
                </section>
              ))}
            </div>
          )}
        </fieldset>

        <fieldset>
          <legend>Sales Tax Registrations</legend>
          <div className="fieldset-title-row">
            <p className="fieldset-description">One recurring registration for each jurisdiction.</p>
            <button
              type="button"
              className="button secondary"
              onClick={() => setForm((current) => ({
                ...current,
                salesTaxRegistrations: [
                  ...current.salesTaxRegistrations,
                  emptySalesTaxRegistration(),
                ],
              }))}
            >
              Add Sales Tax Registration
            </button>
          </div>

          {form.salesTaxRegistrations.length === 0 ? (
            <p className="configuration-empty">No Sales Tax Registrations configured.</p>
          ) : (
            <div className="configuration-list">
              {form.salesTaxRegistrations.map((registration, index) => (
                <section className="configuration-row" key={registration.key}>
                  <header className="configuration-heading">
                    <div>
                      <span>Registration {String(index + 1).padStart(2, "0")}</span>
                      <strong>{registration.jurisdiction || "New registration"}</strong>
                    </div>
                    <button
                      type="button"
                      className="button delete-action"
                      onClick={() => setForm((current) => ({
                        ...current,
                        salesTaxRegistrations: current.salesTaxRegistrations.filter(
                          (_, registrationIndex) => registrationIndex !== index,
                        ),
                      }))}
                    >
                      {registration.id ? "Archive" : "Remove"}
                    </button>
                  </header>
                  <div className="field-grid two-columns">
                    <label>
                      <span>Jurisdiction</span>
                      <input
                        value={registration.jurisdiction}
                        onChange={(event) => updateSalesTax(index, {
                          jurisdiction: event.target.value,
                        })}
                        placeholder="FL"
                        required
                      />
                    </label>
                    <label>
                      <span>Frequency</span>
                      <select
                        value={registration.frequency}
                        onChange={(event) => updateSalesTax(index, {
                          frequency: event.target.value as SalesTaxFrequency,
                        })}
                      >
                        <option value="monthly">Monthly</option>
                        <option value="quarterly">Quarterly</option>
                      </select>
                    </label>
                    <label>
                      <span>Next due date</span>
                      <input
                        type="date"
                        value={registration.next_due_date}
                        onChange={(event) => updateSalesTax(index, {
                          next_due_date: event.target.value,
                        })}
                        required
                      />
                    </label>
                  </div>
                </section>
              ))}
            </div>
          )}
        </fieldset>

        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onCancel}>Cancel</button>
          <button type="submit" className="button primary" disabled={saving}>
            {saving ? "Saving…" : "Save client"}
          </button>
        </div>
      </form>
    </section>
  );
}

export default ClientForm;
