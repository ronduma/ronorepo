/**
 * API calls for the backend's `/api/ollama` model-listing endpoint.
 */

import { apiFetch } from "@/api";

/** Response body returned by `GET /api/ollama/models`. */
export type OllamaModelsResponse = {
  default: string;
  models: string[];
};

/**
 * Lists the models installed on the Ollama server, plus the backend default.
 *
 * @param signal - Optional `AbortSignal` to cancel the in-flight request.
 * @returns The parsed models response body.
 * @throws {ApiError} If the backend or Ollama is unreachable (non-2xx).
 */
export async function getOllamaModels(
  signal?: AbortSignal,
): Promise<OllamaModelsResponse> {
  const response = await apiFetch("/ollama/models", { signal });
  return response.json();
}
