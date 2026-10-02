/**
 * This is the chat provider component for the frontend application.
 * It provides the chat context to its children components.
 */

/* eslint-disable react-refresh/only-export-components */

import { createContext, useContext } from "react";

import { useChat } from "@/hooks/use-chat";

type ChatContextValue = ReturnType<typeof useChat>;

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const chat = useChat();
  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>;
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChatContext must be used within a ChatProvider");
  }
  return context;
}
