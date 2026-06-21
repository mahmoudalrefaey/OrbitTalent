import { motion } from "framer-motion";
import { Logo } from "@/components/logo";

/** Full-screen branded loader — used while the session hydrates. */
export function LoadingScreen({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background">
      <motion.div
        animate={{ scale: [1, 1.08, 1], opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
      >
        <Logo variant="symbol" height={56} />
      </motion.div>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}
