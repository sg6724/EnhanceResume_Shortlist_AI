import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap font-semibold text-sm transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100 disabled:pointer-events-none",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground border border-border hover:bg-bg",
        ok: "bg-ok text-white hover:bg-ok/90",
        danger: "bg-destructive/10 text-destructive border border-destructive/30 hover:bg-destructive/20",
        ghost: "text-muted hover:text-foreground hover:bg-black/[0.04]",
      },
      pill: {
        true: "rounded-full px-6 py-2.5",
        false: "rounded-lg px-4 py-2",
      },
    },
    defaultVariants: {
      variant: "primary",
      pill: false,
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

function Button({ className, variant, pill, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, pill }), className)}
      {...props}
    />
  );
}

export { Button, buttonVariants };
