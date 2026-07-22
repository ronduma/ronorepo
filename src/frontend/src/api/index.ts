const API_BASE = "/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

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
