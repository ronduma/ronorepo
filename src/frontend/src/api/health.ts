import { apiFetch } from "@/api";

export type HealthResponse = {
  status: string;
};

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await apiFetch("/health", { signal });
  return response.json();
}
