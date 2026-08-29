import type { Company, CompanyPayload, Task, TaskStatus } from "./types";

const API_URL = (
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api"
).replace(/\/$/, "");

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message =
      body?.detail ?? "Something went wrong";

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function loginAdmin(password: string) {
  return request<{ authenticated: boolean }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export function getAuthSession() {
  return request<{ authenticated: boolean }>("/auth/session");
}

export function logoutAdmin() {
  return request<void>("/auth/logout", { method: "POST" });
}

export function getTasks(start: string, end: string) {
  const params = new URLSearchParams({ week_start: start, week_end: end });
  return request<Task[]>(`/tasks?${params}`);
}

export async function downloadMonthlyPdf(year: number, month: number) {
  const params = new URLSearchParams({
    year: String(year),
    month: String(month),
  });
  const response = await fetch(`${API_URL}/tasks/monthly-pdf?${params}`, {
    credentials: "include",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Could not download the monthly PDF.");
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const fallbackFilename = `task-schedule-${year}-${String(month).padStart(2, "0")}.pdf`;
  const disposition = response.headers.get("Content-Disposition");
  const filename = disposition?.match(/filename="?([^";]+)"?/i)?.[1] ?? fallbackFilename;
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.hidden = true;
  document.body.appendChild(link);

  try {
    link.click();
  } finally {
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }
}

export function updateTaskStatus(id: number, status: TaskStatus) {
  return request<{ id: number; status: TaskStatus }>(`/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function getClients() {
  return request<Company[]>("/clients");
}

export function createClient(
  payload: CompanyPayload,
) {
  return request<Company>("/clients", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateClient(
  id: number,
  payload: CompanyPayload,
) {
  return request<Company>(`/clients/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteClient(id: number) {
  return request<void>(`/clients/${id}`, {
    method: "DELETE",
  });
}
