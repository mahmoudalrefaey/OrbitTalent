import logoFull from "@/assets/logo-full.png";
import logoSymbol from "@/assets/logo-symbol.png";
import { cn } from "@/lib/utils";

interface LogoProps {
  variant?: "full" | "symbol";
  className?: string;
  /** Pixel height; width auto-scales to preserve aspect ratio. */
  height?: number;
}

/**
 * OrbitTalent logo. `full` = symbol + wordmark (headers, auth, marketing);
 * `symbol` = mark only (sidebar, favicon, compact UI, loaders).
 * Assets are tightly cropped (full ~506x130, symbol 350x350 square), so a
 * given `height` renders the actual artwork at that height with no dead space.
 */
export function Logo({ variant = "full", className, height = 32 }: LogoProps) {
  const src = variant === "full" ? logoFull : logoSymbol;
  return (
    <img
      src={src}
      alt="OrbitTalent"
      height={height}
      style={{ height }}
      className={cn("w-auto select-none", className)}
      draggable={false}
    />
  );
}
