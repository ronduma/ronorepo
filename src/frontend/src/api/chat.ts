import { apiFetch } from "@/api";

/**
 * Streams a chat reply from the backend, chunk by chunk, as they arrive.
 *
 * @remarks
 * Calls `POST /api/chat`, a FastAPI `StreamingResponse` endpoint that does
 * not exist yet on the backend (only `/api/` and `/api/health` are
 * implemented). Callers should catch failures and fall back to a
 * "no backend connected" message until the endpoint ships.
 *
 * @param message - The user's chat message to send.
 * @param signal - Optional `AbortSignal` to cancel the in-flight request.
 * @returns An async generator yielding decoded text chunks as they stream in.
 * @throws {ApiError} If the request fails with a non-2xx response.
 * @throws {Error} If the response has no readable body.
 */
export async function* streamChatReply(
  message: string,
  signal?: AbortSignal,
): AsyncGenerator<string> {
  const response = await apiFetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  });

  if (!response.body) {
    throw new Error("POST /chat returned no response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      if (chunk) yield chunk;
    }
  } finally {
    reader.releaseLock();
  }
}
