import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full text-[11px] px-2 py-0.5 font-medium w-fit",
  {
    variants: {
      tone: {
        ok: "bg-ok/15 text-ok",
        bad: "bg-bad/15 text-bad",
        warn: "bg-warn/15 text-warn",
        accent: "bg-accent/15 text-accent",
        muted: "bg-muted/15 text-muted",
      },
    },
    defaultVariants: {
      tone: "muted",
    },
  }
);

export type Tone = NonNullable<VariantProps<typeof badgeVariants>["tone"]>;

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  asChild?: boolean;
}

function Badge({ className, tone, asChild = false, ...props }: BadgeProps) {
  const Comp = asChild ? Slot : "span";
  return <Comp data-slot="badge" className={cn(badgeVariants({ tone }), className)} {...props} />;
}

export { Badge, badgeVariants };
