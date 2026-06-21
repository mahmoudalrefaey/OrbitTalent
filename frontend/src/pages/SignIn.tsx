import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  Loader2,
  ArrowRight,
  Check,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/context/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/misc";
import { Logo } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const VALUE_PROPS = [
  "Screen every CV in seconds, not hours",
  "Hybrid keyword + AI scoring you can trust",
  "Shortlist top candidates with one click",
];

/** Marketing panel shown on the right at lg+ — shared visual language with SignUp. */
function BrandPanel({
  headline,
  subline,
}: {
  headline: string;
  subline: string;
}) {
  return (
    <div className="relative hidden overflow-hidden bg-gradient-to-br from-primary to-primary/80 lg:flex lg:w-1/2">
      {/* decorative orbits */}
      <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full border border-white/10" />
      <div className="pointer-events-none absolute -bottom-32 -left-20 h-[28rem] w-[28rem] rounded-full border border-white/10" />
      <div className="pointer-events-none absolute right-10 bottom-16 h-40 w-40 rounded-full bg-white/5 blur-2xl" />

      <div className="relative z-10 flex w-full flex-col justify-between p-12 text-white">
        <Link
          to="/"
          className="inline-flex w-fit items-center rounded-xl bg-white px-4 py-3 shadow-sm transition-transform hover:scale-[1.02]"
        >
          <Logo variant="full" height={30} />
        </Link>

        <div className="max-w-md">
          <span className="mb-5 inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-medium backdrop-blur">
            <Sparkles className="h-3.5 w-3.5" />
            AI-powered CV screening
          </span>
          <h2 className="text-3xl font-bold leading-tight tracking-tight">
            {headline}
          </h2>
          <p className="mt-3 text-base text-white/80">{subline}</p>

          <ul className="mt-8 space-y-4">
            {VALUE_PROPS.map((v) => (
              <li key={v} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/20">
                  <Check className="h-4 w-4" />
                </span>
                <span className="text-sm text-white/90">{v}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex items-center gap-3 text-sm text-white/80">
          <div className="flex -space-x-2">
            {["bg-white/30", "bg-white/40", "bg-white/50"].map((c, i) => (
              <span
                key={i}
                className={cn(
                  "h-8 w-8 rounded-full border-2 border-primary",
                  c
                )}
              />
            ))}
          </div>
          <span>Trusted by hiring teams screening 10,000+ CVs</span>
        </div>
      </div>
    </div>
  );
}

export default function SignIn() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>(
    {}
  );
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Already authenticated → bounce to the app.
  useEffect(() => {
    if (user) nav("/app", { replace: true });
  }, [user, nav]);

  const emailError =
    !email.trim()
      ? "Email is required"
      : !EMAIL_RE.test(email)
      ? "Enter a valid email address"
      : null;
  const passwordError = !password ? "Password is required" : null;

  const showEmailError = (touched.email || submitted) && emailError;
  const showPasswordError = (touched.password || submitted) && passwordError;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    setFormError(null);
    if (emailError || passwordError) return;

    setSubmitting(true);
    try {
      await login(email.trim(), password);
      nav(from || "/app", { replace: true });
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Something went wrong. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-background">
      {/* Form side */}
      <div className="relative flex w-full flex-col lg:w-1/2">
        <div className="absolute right-4 top-4 z-10">
          <ThemeToggle />
        </div>

        <div className="flex flex-1 items-center justify-center px-6 py-12">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="w-full max-w-md"
          >
            {/* Mobile logo */}
            <Link
              to="/"
              className="mb-8 flex w-fit items-center lg:hidden"
              aria-label="OrbitTalent home"
            >
              <Logo variant="full" height={32} />
            </Link>

            <div className="mb-8">
              <h1 className="text-2xl font-bold tracking-tight text-foreground">
                Welcome back
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Sign in to continue screening candidates with OrbitTalent.
              </p>
            </div>

            <AnimatePresence>
              {formError && (
                <motion.div
                  initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                  animate={{ opacity: 1, height: "auto", marginBottom: 24 }}
                  exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                  transition={{ duration: 0.25 }}
                  className="overflow-hidden"
                >
                  <div
                    role="alert"
                    className="flex items-start gap-3 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger"
                  >
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{formError}</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <form onSubmit={handleSubmit} noValidate className="space-y-5">
              {/* Email */}
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@company.com"
                    className="pl-9"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onBlur={() => setTouched((t) => ({ ...t, email: true }))}
                    aria-invalid={!!showEmailError}
                    aria-describedby={showEmailError ? "email-error" : undefined}
                  />
                </div>
                <AnimatePresence>
                  {showEmailError && (
                    <motion.p
                      id="email-error"
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="flex items-center gap-1.5 text-xs text-danger"
                    >
                      <AlertCircle className="h-3.5 w-3.5" />
                      {emailError}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <button
                    type="button"
                    title="Coming soon"
                    className="text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    className="px-9"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onBlur={() => setTouched((t) => ({ ...t, password: true }))}
                    aria-invalid={!!showPasswordError}
                    aria-describedby={
                      showPasswordError ? "password-error" : undefined
                    }
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((s) => !s)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <AnimatePresence>
                  {showPasswordError && (
                    <motion.p
                      id="password-error"
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="flex items-center gap-1.5 text-xs text-danger"
                    >
                      <AlertCircle className="h-3.5 w-3.5" />
                      {passwordError}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>

              <Button
                type="submit"
                size="lg"
                className="w-full"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            <p className="mt-8 text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link
                to="/signup"
                className="font-medium text-primary underline-offset-4 hover:underline"
              >
                Sign up
              </Link>
            </p>
          </motion.div>
        </div>
      </div>

      <BrandPanel
        headline="Hire smarter, not harder."
        subline="OrbitTalent ranks every applicant so your team spends time on people, not paperwork."
      />
    </div>
  );
}
