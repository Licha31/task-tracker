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
