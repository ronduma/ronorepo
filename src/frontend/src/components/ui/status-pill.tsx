import { cn } from "@/lib/utils";
import { useHealth } from "@/hooks/use-health";

const STATUS_LABEL: Record<string, string> = {
  checking: "checking",
  ok: "online",
  error: "offline",
};

const STATUS_DOT: Record<string, string> = {
  checking: "bg-muted-foreground",
  ok: "bg-success",
  error: "bg-destructive",
};

export function StatusPill() {
  const { status } = useHealth();

  return (
    <div
      className="flex items-center gap-2 rounded-full border px-2.5 py-1 font-mono text-xs text-muted-foreground"
      aria-live="polite"
    >
      <span className="relative flex size-2">
        {status === "ok" && (
          <span
            className={cn(
              "absolute inline-flex size-full animate-ping rounded-full opacity-75",
              STATUS_DOT[status],
            )}
          />
        )}
        <span
          className={cn(
            "relative inline-flex size-2 rounded-full",
            STATUS_DOT[status],
          )}
        />
      </span>
      <span>api · {STATUS_LABEL[status]}</span>
    </div>
  );
}
