/**
 * Dropdown for choosing which Ollama model the chatbot talks to.
 * Renders nothing until the backend has reported the available models.
 */

// shadcn components
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// lucide icons
import { ChevronDown } from "lucide-react";

export function ModelSelect({
  models,
  value,
  onChange,
  disabled,
}: {
  models: string[];
  value: string | null;
  onChange: (model: string) => void;
  disabled?: boolean;
}) {
  if (models.length === 0 || !value) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        disabled={disabled}
        render={
          <Button variant="ghost" size="sm" className="font-mono text-xs">
            {value}
            <ChevronDown className="size-3" />
          </Button>
        }
      />
      <DropdownMenuContent align="start">
        <DropdownMenuRadioGroup value={value} onValueChange={onChange}>
          {models.map((model) => (
            <DropdownMenuRadioItem key={model} value={model}>
              {model}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
