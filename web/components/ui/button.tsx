import { Slot } from "@radix-ui/react-slot";
import { type VariantProps, cva } from "class-variance-authority";
import { type ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap",
    "rounded-[var(--radius-pill)] text-sm font-medium",
    "transition-[background-color,box-shadow,transform] duration-150",
    "disabled:opacity-50 disabled:pointer-events-none",
    "active:scale-[0.98] select-none",
  ].join(" "),
  {
    variants: {
      variant: {
        primary:
          "bg-[color:var(--color-brand)] text-[color:var(--color-brand-fg)] shadow-[var(--shadow-pop)] hover:brightness-105",
        secondary:
          "bg-[color:var(--color-surface-2)] text-[color:var(--color-fg)] hover:bg-[color:var(--color-border)]",
        outline:
          "border border-[color:var(--color-border)] bg-transparent hover:bg-[color:var(--color-surface-2)]",
        ghost: "bg-transparent hover:bg-[color:var(--color-surface-2)]",
        danger: "bg-[color:var(--color-danger)] text-white hover:brightness-105",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10 p-0",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, asChild, type, ...props },
  ref,
) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      ref={ref}
      type={asChild ? undefined : (type ?? "button")}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
});

export { buttonVariants };
