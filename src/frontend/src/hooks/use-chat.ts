/**
 * This is a custom React hook for managing chat functionality in the frontend application.
 */

import { useCallback, useRef, useState } from "react";

import { streamChatReply } from "@/api/chat";
import type { ChatMessage } from "@/components/chat/types";

const NO_BACKEND_MESSAGE =
  "Couldn't reach the model. Check that the backend and Ollama are running.";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isAssistantTyping, setIsAssistantTyping] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed) return;

      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
        createdAt: Date.now(),
      };

      // history sent to the model: prior turns that actually got a reply
      const history = [...messages, userMessage]
        .filter((m) => m.content && m.content !== NO_BACKEND_MESSAGE)
        .map(({ role, content }) => ({ role, content }));

      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        userMessage,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          createdAt: Date.now(),
        },
      ]);
      setIsAssistantTyping(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        let received = false;
        for await (const chunk of streamChatReply(history, controller.signal)) {
          received = true;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + chunk } : m,
            ),
          );
        }
        if (!received) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: NO_BACKEND_MESSAGE } : m,
            ),
          );
        }
      } catch {
        if (controller.signal.aborted) return;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: NO_BACKEND_MESSAGE } : m,
          ),
        );
      } finally {
        // a reset may have superseded this request; don't clobber newer state
        if (abortRef.current === controller) {
          setIsAssistantTyping(false);
          abortRef.current = null;
        }
      }
    },
    [messages],
  );

  const resetChat = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setIsAssistantTyping(false);
  }, []);

  return { messages, isAssistantTyping, sendMessage, resetChat };
}
