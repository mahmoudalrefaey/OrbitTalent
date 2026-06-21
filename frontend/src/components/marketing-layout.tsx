import { Link, Outlet, useLocation } from "react-router-dom";
import { buttonVariants } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";

export function MarketingLayout() {
  const { pathname } = useLocation();
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur-lg">
        <div className="container flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center">
            <Logo variant="full" height={32} />
          </Link>
          <nav className="hidden items-center gap-6 text-sm font-medium md:flex">
            <Link
              to="/"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              Product
            </Link>
            <Link
              to="/pricing"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              Pricing
            </Link>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link
              to="/signin"
              className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
            >
              Sign in
            </Link>
            <Link to="/signup" className={cn(buttonVariants({ size: "sm" }))}>
              Get started
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet key={pathname} />
      </main>

      <footer className="border-t border-border/60 py-10">
        <div className="container flex flex-col items-center justify-between gap-4 text-sm text-muted-foreground sm:flex-row">
          <div className="flex items-center gap-2">
            <Logo variant="symbol" height={22} />
            <span>© {new Date().getFullYear()} OrbitTalent. All rights reserved.</span>
          </div>
          <div className="flex gap-6">
            <Link to="/pricing" className="hover:text-foreground">
              Pricing
            </Link>
            <Link to="/app" className="hover:text-foreground">
              Dashboard
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
