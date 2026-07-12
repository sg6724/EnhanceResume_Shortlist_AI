import * as React from "react";
import { cn } from "@/lib/utils";

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "w-full bg-bg border border-input rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted",
        "focus:outline-none focus:border-primary transition-colors resize-none",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className
      )}
      {...props}
    />
  );
}

export { Textarea };
