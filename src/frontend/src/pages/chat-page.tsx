/**
 * This is the chat page component for the frontend application.
 * It displays the chat interface, including the chat thread and input.
 */

// providers
import { useChatContext } from "@/components/chat/chat-provider";

// custom components
import { ChatEmptyState } from "@/components/chat/chat-empty-state";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatThread } from "@/components/chat/chat-thread";

export function ChatPage() {
  const { messages, isAssistantTyping, sendMessage } = useChatContext();

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {messages.length === 0 ? (
        <ChatEmptyState />
      ) : (
        <ChatThread messages={messages} />
      )}
      <ChatInput onSend={sendMessage} disabled={isAssistantTyping} />
    </div>
  );
}
