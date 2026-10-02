/**
 * This is the chat input component for the frontend application.
 * It allows users to enter messages and send them.
 */

import { useState } from "react";
import type { KeyboardEvent } from "react";

// shadcn components
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

// lucide icons
import { ArrowUp, Square } from "lucide-react";

export function ChatInput({
  onSend,
  onStop,
  isGenerating,
  toolbar,
}: {
  onSend: (content: string) => void;
  onStop: () => void;
  isGenerating?: boolean;
  toolbar?: React.ReactNode;
}) {
  const [draft, setDraft] = useState("");

  const submit = () => {
    if (!draft.trim() || isGenerating) return;
    onSend(draft);
    setDraft("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-4">
      <div className="flex items-end gap-2 rounded-2xl border bg-card p-2 shadow-sm">
        <Textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message ronorepo..."
          className="min-h-9 max-h-48 resize-none border-none bg-transparent px-2 py-1.5 shadow-none focus-visible:ring-0"
        />
        {isGenerating ? (
          <Button
            size="icon"
            variant="outline"
            onClick={onStop}
            className="shrink-0"
          >
            <Square className="size-4" />
            <span className="sr-only">Stop generating</span>
          </Button>
        ) : (
          <Button
            size="icon"
            onClick={submit}
            disabled={!draft.trim()}
            className={cn(
              "shrink-0 bg-signal text-signal-foreground hover:bg-signal/80",
            )}
          >
            <ArrowUp className="size-4" />
            <span className="sr-only">Send message</span>
          </Button>
        )}
      </div>
      {toolbar && <div className="mt-1 flex px-1">{toolbar}</div>}
    </div>
  );
}
