/**
 * This is a custom React hook for managing chat functionality in the frontend application.
 */

import { useCallback, useRef, useState } from "react";

import { streamChatReply } from "@/api/chat";
import type { ChatMessage } from "@/components/chat/types";

const NO_BACKEND_MESSAGE =
  "This is a UI preview — no backend is connected yet.";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isAssistantTyping, setIsAssistantTyping] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      createdAt: Date.now(),
    };

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
      for await (const chunk of streamChatReply(trimmed, controller.signal)) {
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
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: NO_BACKEND_MESSAGE } : m,
        ),
      );
    } finally {
      setIsAssistantTyping(false);
      abortRef.current = null;
    }
  }, []);

  const resetChat = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setIsAssistantTyping(false);
  }, []);

  return { messages, isAssistantTyping, sendMessage, resetChat };
}
