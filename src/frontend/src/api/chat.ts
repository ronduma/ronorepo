/**
 * API calls for the backend's Ollama chat endpoint.
 */

import { apiFetch } from "@/api";

/** A single conversation turn as expected by `POST /api/ollama/chat`. */
export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
};

/**
 * Streams a chat reply from the backend, chunk by chunk, as they arrive.
 *
 * @remarks
 * Calls `POST /api/ollama/chat`, which proxies to the local Ollama server
 * and streams the model's reply back as plain text.
 *
 * @param messages - The conversation so far, ending with the new user message.
 * @param signal - Optional `AbortSignal` to cancel the in-flight request.
 * @returns An async generator yielding decoded text chunks as they stream in.
 * @throws {ApiError} If the request fails with a non-2xx response.
 * @throws {Error} If the response has no readable body.
 */
export async function* streamChatReply(
  messages: ChatTurn[],
  signal?: AbortSignal,
): AsyncGenerator<string> {
  const response = await apiFetch("/ollama/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!response.body) {
    throw new Error("POST /ollama/chat returned no response body");
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
