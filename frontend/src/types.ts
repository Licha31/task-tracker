export type PayrollFrequency =
  | "weekly"
  | "biweekly"
  | "semi_monthly"
  | "monthly";

export type SalesTaxFrequency =
  | "monthly"
  | "quarterly";

export type PayrollSchedule = {
  id: number;
  label: string;
  jurisdiction: string;
  sui_id: string | null;
  sit_id: string | null;
  principal_owner: string | null;
  frequency: PayrollFrequency;
  payroll_platform: string;
  next_pay_date: string;
  next_process_date: string;
  semi_monthly_day_1: number | null;
  semi_monthly_day_2: number | null;
};

export type SalesTaxRegistration = {
  id: number;
  jurisdiction: string;
  frequency: SalesTaxFrequency;
  next_due_date: string;
};

export type Company = {
  id: number;
  name: string;
  ein: string;
  payroll_schedules: PayrollSchedule[];
  sales_tax_registrations: SalesTaxRegistration[];
};

export type PayrollScheduleInput = Omit<PayrollSchedule, "id"> & { id?: number };
export type SalesTaxRegistrationInput = Omit<SalesTaxRegistration, "id"> & { id?: number };

export type CompanyPayload = {
  name: string;
  ein: string;
  payroll_schedules: PayrollScheduleInput[];
  sales_tax_registrations: SalesTaxRegistrationInput[];
};

export type TaskStatus = "pending" | "in_progress" | "completed";

export type Task = {
  id: number;
  company_name: string;
  task_type: "payroll" | "sales_tax";
  source_label: string | null;
  source_jurisdiction: string;
  process_date: string | null;
  pay_date: string | null;
  due_date: string | null;
  status: TaskStatus;
};
