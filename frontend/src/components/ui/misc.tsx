import { forwardRef, type HTMLAttributes, type LabelHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Label = forwardRef<HTMLLabelElement, LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => (
    <label
      ref={ref}
      className={cn("text-sm font-medium text-foreground", className)}
      {...props}
    />
  )
);
Label.displayName = "Label";

/** Determinate progress bar. value is 0-100. tone shifts color by threshold. */
export function Progress({
  value,
  className,
  tone = "auto",
}: {
  value: number;
  className?: string;
  tone?: "auto" | "primary";
}) {
  const v = Math.max(0, Math.min(100, value));
  const color =
    tone === "primary"
      ? "bg-primary"
      : v >= 70
      ? "bg-success"
      : v >= 40
      ? "bg-warning"
      : "bg-danger";
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-muted", className)}>
      <div
        className={cn("h-full rounded-full transition-all duration-500", color)}
        style={{ width: `${v}%` }}
      />
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton", className)} />;
}

export function Separator({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("h-px w-full bg-border", className)} {...props} />;
}
