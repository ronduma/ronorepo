/**
 * API calls for the backend's `/api/health` liveness endpoint.
 */

import { apiFetch } from "@/api";

/** Response body returned by `GET /api/health`. */
export type HealthResponse = {
  status: string;
};

/**
 * Checks whether the backend is reachable and healthy.
 *
 * @param signal - Optional `AbortSignal` to cancel the in-flight request.
 * @returns The parsed health response body.
 * @throws {ApiError} If the request fails with a non-2xx response.
 */
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await apiFetch("/health", { signal });
  return response.json();
}
