import type { ReactNode } from "react";

export function PageHeader({
  title, description, action,
}: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-text">{title}</h1>
        {description && <p className="text-muted text-sm mt-1.5 max-w-2xl">{description}</p>}
      </div>
      {action}
    </div>
  );
}
