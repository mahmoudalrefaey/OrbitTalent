import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6 text-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col items-center"
      >
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          className="text-7xl"
          aria-hidden
        >
          🛰️
        </motion.div>
        <h1 className="mt-6 text-5xl font-bold tracking-tight">404</h1>
        <p className="mt-2 text-xl font-semibold">Lost in orbit</p>
        <p className="mt-3 max-w-md text-muted-foreground">
          The page you are looking for drifted off into deep space. Let's get you
          back to mission control.
        </p>
        <Link to="/" className={cn(buttonVariants({ size: "lg" }), "mt-8")}>
          Back home
        </Link>
      </motion.div>
    </div>
  );
}
