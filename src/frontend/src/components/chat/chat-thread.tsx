/**
 * This is the chat thread component for the frontend application.
 * It displays a list of chat messages in a scrollable area.
 */

import { useEffect, useRef } from "react";

// types
import type { ChatMessage as ChatMessageType } from "@/components/chat/types";

// shadcn components
import { ScrollArea } from "@/components/ui/scroll-area";

// custom components
import { ChatMessage } from "@/components/chat/chat-message";

export function ChatThread({ messages }: { messages: ChatMessageType[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
