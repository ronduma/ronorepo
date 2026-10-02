/**
 * This is the chat empty state component for the frontend application.
 * It displays a splash message when the chat is empty.
 */

// lucide icons
import { Sparkles } from "lucide-react";

export function ChatEmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 text-center">
      <div className="flex size-10 items-center justify-center rounded-full border text-muted-foreground">
        <Sparkles className="size-5" />
      </div>
      <h1 className="text-xl font-medium">What's on your mind?</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        Start a conversation below — this is a preview interface for ronorepo's
        control panel.
      </p>
    </div>
  );
}
