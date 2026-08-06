import type { ReactNode } from "react";
import { GlowBackground } from "@/components/ui/GlowBackground";

export function PageHeader({
  title, titleEmphasis, description, action,
}: { title: string; titleEmphasis?: string; description?: string; action?: ReactNode }) {
  return (
    <div className="relative">
      <GlowBackground />
      <div className="flex items-start justify-between gap-4 flex-wrap relative">
        <div>
          <h1 className="font-display text-4xl tracking-tight text-text">
            {title} {titleEmphasis && <em className="italic">{titleEmphasis}</em>}
          </h1>
          {description && <p className="text-muted text-sm mt-2 max-w-2xl">{description}</p>}
        </div>
        {action}
      </div>
    </div>
  );
}
