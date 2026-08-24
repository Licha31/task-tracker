export type PayrollFrequency =
  | "weekly"
  | "biweekly"
  | "semi_monthly"
  | "monthly";

export type SalesTaxFrequency =
  | "monthly"
  | "quarterly";

export type PayrollProfile = {
  id: number;
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

export type SalesTaxProfile = {
  id: number;
  frequency: SalesTaxFrequency;
  next_due_date: string;
};

export type Company = {
  id: number;
  name: string;
  ein: string;
  payroll: PayrollProfile | null;
  sales_tax: SalesTaxProfile | null;
};

export type CompanyPayload = {
  name: string;
  ein: string;
  payroll: Omit<PayrollProfile, "id"> | null;
  sales_tax: Omit<SalesTaxProfile, "id"> | null;
};

export type TaskStatus = "pending" | "in_progress" | "completed";

export type Task = {
  id: number;
  company_name: string;
  task_type: "payroll" | "sales_tax";
  process_date: string | null;
  pay_date: string | null;
  due_date: string | null;
  status: TaskStatus;
};
