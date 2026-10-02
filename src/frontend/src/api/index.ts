/**
 * Shared HTTP client for the backend API.
 *
 * Every request goes through `apiFetch`, which prefixes paths with `/api`
 * and normalizes non-2xx responses into a typed `ApiError` so callers don't
 * need to check `response.ok` themselves.
 */

const API_BASE = "/api";

/** Thrown by `apiFetch` when the backend responds with a non-2xx status. */
export class ApiError extends Error {
  status: number;

  /**
   * @param status - The HTTP status code returned by the backend.
   * @param message - A human-readable description of the failure.
   */
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Fetches a path under the backend's `/api` prefix.
 *
 * @param path - The API path to request, e.g. `/health` (joined onto `/api`).
 * @param init - Standard `fetch` options (method, headers, body, signal, etc.).
 * @returns The raw `Response` on success.
 * @throws {ApiError} If the response status is not in the 2xx range.
 */
export async function apiFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const response = await fetch(`${API_BASE}${path}`, init);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `${init?.method ?? "GET"} ${path} failed with ${response.status}`,
    );
  }

  return response;
}
