import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mail,
  Lock,
  User as UserIcon,
  Building2,
  Briefcase,
  Eye,
  EyeOff,
  AlertCircle,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Check,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { ApiError } from "@/api/client";
import { useAuth } from "@/context/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label, Progress } from "@/components/ui/misc";
import { Logo } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const VALUE_PROPS = [
  "Set up your first job and start screening in minutes",
  "Transparent scores you can defend to any stakeholder",
  "Your jobs and candidates stay private to your account",
];

const STRENGTH_LABELS = ["Weak", "Weak", "Fair", "Good", "Strong"] as const;

/** 0-4 password strength score. */
function scorePassword(pw: string): number {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return score;
}

function BrandPanel() {
  return (
    <div className="relative hidden overflow-hidden bg-gradient-to-br from-primary to-primary/80 lg:flex lg:w-1/2">
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
            Start free today
          </span>
          <h2 className="text-3xl font-bold leading-tight tracking-tight">
            Build your shortlist in minutes.
          </h2>
          <p className="mt-3 text-base text-white/80">
            Join hiring teams who let OrbitTalent do the first pass — so they
            interview the right people, faster.
          </p>

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

        <p className="text-sm text-white/70">
          Explainable, cost-optimized CV screening.
        </p>
      </div>
    </div>
  );
}

export default function SignUp() {
  const { user, register } = useAuth();
  const nav = useNavigate();

  const [step, setStep] = useState<1 | 2>(1);
  const [direction, setDirection] = useState<1 | -1>(1);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  // Presentation-only — not sent to the backend.
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");

  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>(
    {}
  );
  const [emailConflict, setEmailConflict] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (user) nav("/app", { replace: true });
  }, [user, nav]);

  const emailValid = EMAIL_RE.test(email);
  const passwordLongEnough = password.length >= 8;
  const strength = scorePassword(password);

  const emailError =
    !email.trim()
      ? "Email is required"
      : !emailValid
      ? "Enter a valid email address"
      : null;
  const passwordError =
    !password
      ? "Password is required"
      : !passwordLongEnough
      ? "Use at least 8 characters"
      : null;

  const showEmailError =
    (touched.email && emailError) || (emailConflict ? "This email is already in use" : null);
  const showPasswordError = touched.password && passwordError;

  const canContinue = emailValid && passwordLongEnough;

  function goToStep2() {
    setTouched({ email: true, password: true });
    setFormError(null);
    if (!canContinue) return;
    setDirection(1);
    setStep(2);
  }

  function backToStep1() {
    setDirection(-1);
    setStep(1);
  }

  async function createAccount() {
    setFormError(null);
    setSubmitting(true);
    try {
      await register(email.trim(), password, name.trim());
      nav("/onboarding", { replace: true });
    } catch (err) {
      const isConflict =
        err instanceof ApiError && err.status === 409;
      setFormError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again."
      );
      if (isConflict || (err instanceof Error && /already registered/i.test(err.message))) {
        setEmailConflict(true);
        setDirection(-1);
        setStep(1);
        setTouched((t) => ({ ...t, email: true }));
        // focus the email field after the step transition settles
        setTimeout(() => emailRef.current?.focus(), 350);
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleStep2Submit(e: FormEvent) {
    e.preventDefault();
    createAccount();
  }

  const slideVariants = {
    enter: (dir: 1 | -1) => ({ x: dir * 40, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: 1 | -1) => ({ x: dir * -40, opacity: 0 }),
  };

  return (
    <div className="flex min-h-screen bg-background">
      <BrandPanel />

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

            {/* Header + step indicator */}
            <div className="mb-6">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Step {step} of 2
                </span>
                <div className="flex gap-1.5">
                  <span
                    className={cn(
                      "h-1.5 w-8 rounded-full transition-colors",
                      step >= 1 ? "bg-primary" : "bg-muted"
                    )}
                  />
                  <span
                    className={cn(
                      "h-1.5 w-8 rounded-full transition-colors",
                      step >= 2 ? "bg-primary" : "bg-muted"
                    )}
                  />
                </div>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">
                {step === 1 ? "Create your account" : "Tell us a bit about you"}
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {step === 1
                  ? "It only takes a minute to get started."
                  : "Optional — this helps tailor OrbitTalent. You can skip it."}
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

            <div className="relative overflow-hidden">
              <AnimatePresence mode="wait" custom={direction}>
                {step === 1 ? (
                  <motion.div
                    key="step1"
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                  >
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        goToStep2();
                      }}
                      noValidate
                      className="space-y-5"
                    >
                      {/* Name */}
                      <div className="space-y-1.5">
                        <Label htmlFor="name">
                          Name{" "}
                          <span className="font-normal text-muted-foreground">
                            (optional)
                          </span>
                        </Label>
                        <div className="relative">
                          <UserIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                          <Input
                            id="name"
                            type="text"
                            autoComplete="name"
                            placeholder="Jane Doe"
                            className="pl-9"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                          />
                        </div>
                      </div>

                      {/* Email */}
                      <div className="space-y-1.5">
                        <Label htmlFor="email">Email</Label>
                        <div className="relative">
                          <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                          <Input
                            id="email"
                            ref={emailRef}
                            type="email"
                            autoComplete="email"
                            placeholder="you@company.com"
                            className={cn(
                              "pl-9",
                              emailConflict &&
                                "border-danger focus-visible:ring-danger"
                            )}
                            value={email}
                            onChange={(e) => {
                              setEmail(e.target.value);
                              if (emailConflict) setEmailConflict(false);
                            }}
                            onBlur={() =>
                              setTouched((t) => ({ ...t, email: true }))
                            }
                            aria-invalid={!!showEmailError}
                            aria-describedby={
                              showEmailError ? "email-error" : undefined
                            }
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
                              {showEmailError}
                            </motion.p>
                          )}
                        </AnimatePresence>
                      </div>

                      {/* Password */}
                      <div className="space-y-1.5">
                        <Label htmlFor="password">Password</Label>
                        <div className="relative">
                          <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                          <Input
                            id="password"
                            type={showPassword ? "text" : "password"}
                            autoComplete="new-password"
                            placeholder="Create a password"
                            className="px-9"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            onBlur={() =>
                              setTouched((t) => ({ ...t, password: true }))
                            }
                            aria-invalid={!!showPasswordError}
                            aria-describedby="password-help"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword((s) => !s)}
                            aria-label={
                              showPassword ? "Hide password" : "Show password"
                            }
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                          >
                            {showPassword ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </button>
                        </div>

                        {/* Strength meter */}
                        <AnimatePresence>
                          {password && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: "auto" }}
                              exit={{ opacity: 0, height: 0 }}
                              className="space-y-1 overflow-hidden pt-1"
                            >
                              <Progress value={(strength / 4) * 100} />
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-muted-foreground">
                                  Password strength
                                </span>
                                <span
                                  className={cn(
                                    "text-xs font-medium",
                                    strength <= 1
                                      ? "text-danger"
                                      : strength === 2
                                      ? "text-warning"
                                      : "text-success"
                                  )}
                                >
                                  {STRENGTH_LABELS[strength]}
                                </span>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>

                        <AnimatePresence>
                          {showPasswordError ? (
                            <motion.p
                              id="password-help"
                              initial={{ opacity: 0, y: -4 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -4 }}
                              className="flex items-center gap-1.5 text-xs text-danger"
                            >
                              <AlertCircle className="h-3.5 w-3.5" />
                              {passwordError}
                            </motion.p>
                          ) : (
                            <p
                              id="password-help"
                              className="text-xs text-muted-foreground"
                            >
                              At least 8 characters
                            </p>
                          )}
                        </AnimatePresence>
                      </div>

                      <Button
                        type="submit"
                        size="lg"
                        className="w-full"
                        disabled={!canContinue}
                      >
                        Continue
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </form>
                  </motion.div>
                ) : (
                  <motion.div
                    key="step2"
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                  >
                    <form onSubmit={handleStep2Submit} className="space-y-5">
                      {/* Company */}
                      <div className="space-y-1.5">
                        <Label htmlFor="company">
                          Company{" "}
                          <span className="font-normal text-muted-foreground">
                            (optional)
                          </span>
                        </Label>
                        <div className="relative">
                          <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                          <Input
                            id="company"
                            type="text"
                            autoComplete="organization"
                            placeholder="Acme Inc."
                            className="pl-9"
                            value={company}
                            onChange={(e) => setCompany(e.target.value)}
                          />
                        </div>
                      </div>

                      {/* Role */}
                      <div className="space-y-1.5">
                        <Label htmlFor="role">
                          Your role{" "}
                          <span className="font-normal text-muted-foreground">
                            (optional)
                          </span>
                        </Label>
                        <div className="relative">
                          <Briefcase className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                          <Input
                            id="role"
                            type="text"
                            autoComplete="organization-title"
                            placeholder="Recruiter, Hiring Manager…"
                            className="pl-9"
                            value={role}
                            onChange={(e) => setRole(e.target.value)}
                          />
                        </div>
                      </div>

                      <div className="flex items-center gap-3 rounded-lg bg-secondary/60 px-4 py-3 text-xs text-muted-foreground">
                        <ShieldCheck className="h-4 w-4 shrink-0 text-primary" />
                        <span>
                          We&apos;ll never share your details. You can change
                          these anytime.
                        </span>
                      </div>

                      <div className="space-y-3">
                        <Button
                          type="submit"
                          size="lg"
                          className="w-full"
                          disabled={submitting}
                        >
                          {submitting ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Creating account…
                            </>
                          ) : (
                            <>
                              Create account
                              <ArrowRight className="h-4 w-4" />
                            </>
                          )}
                        </Button>

                        <div className="flex items-center justify-between">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={backToStep1}
                            disabled={submitting}
                          >
                            <ArrowLeft className="h-4 w-4" />
                            Back
                          </Button>
                          <Button
                            type="button"
                            variant="link"
                            size="sm"
                            onClick={createAccount}
                            disabled={submitting}
                          >
                            Skip for now
                          </Button>
                        </div>
                      </div>
                    </form>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <p className="mt-6 text-center text-xs text-muted-foreground">
              By continuing you agree to our{" "}
              <button
                type="button"
                title="Coming soon"
                className="underline underline-offset-2 hover:text-foreground"
              >
                Terms
              </button>{" "}
              and{" "}
              <button
                type="button"
                title="Coming soon"
                className="underline underline-offset-2 hover:text-foreground"
              >
                Privacy Policy
              </button>
              .
            </p>

            <p className="mt-6 text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link
                to="/signin"
                className="font-medium text-primary underline-offset-4 hover:underline"
              >
                Sign in
              </Link>
            </p>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
