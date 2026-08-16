"use client";

import { motion } from "framer-motion";
import { AlertCircle, ArrowLeft, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { BetaBadge } from "@/components/app-shell";
import { useMe } from "@/components/portal/use-me";
import { loginUrl } from "@/lib/portal-api";

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-4.5" aria-hidden>
      <path
        fill="#4285F4"
        d="M23.5 12.3c0-.9-.1-1.5-.3-2.2H12v4.1h6.5c-.1 1.1-.8 2.7-2.4 3.8l3.6 2.8c2.2-2 3.8-5 3.8-8.5z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.2 0 6-1.1 7.9-2.9l-3.6-2.8c-1 .7-2.4 1.2-4.3 1.2-3.3 0-6.1-2.2-7.1-5.2L1.2 17C3.2 21.1 7.3 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M4.9 14.3c-.3-.8-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.2 6.9C.4 8.5 0 10.2 0 12s.4 3.5 1.2 5.1l3.7-2.8z"
      />
      <path
        fill="#EA4335"
        d="M12 4.6c1.8 0 3 .8 3.7 1.4l3.2-3.1C17 1.1 14.7 0 12 0 7.3 0 3.2 2.9 1.2 6.9l3.7 2.8c1-3 3.8-5.1 7.1-5.1z"
      />
    </svg>
  );
}

function AuthCardInner({ mode }: { mode: "signin" | "signup" }) {
  const router = useRouter();
  const { data: me } = useMe();
  const searchParams = useSearchParams();
  const oauthError = searchParams.get("error");

  // Already signed in? Straight to the dashboard.
  useEffect(() => {
    if (me) router.replace("/home");
  }, [me, router]);

  const isSignup = mode === "signup";

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-sm">
        <Link
          href="/"
          className="mb-6 flex items-center gap-1.5 text-xs text-faint transition-colors duration-100 hover:text-muted"
        >
          <ArrowLeft className="size-3.5" /> Back
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="glass p-8"
        >
          <div className="flex items-center justify-between">
            <span className="grid size-9 place-items-center rounded-md bg-accent-2">
              <Sparkles className="size-5 text-white" />
            </span>
            <BetaBadge />
          </div>

          <h1 className="mt-5 text-xl font-semibold">
            {isSignup ? "Get access to the library" : "Welcome back"}
          </h1>
          <p className="mt-1.5 text-sm leading-relaxed text-muted">
            {isSignup
              ? "Your Google account becomes your Sourcerer account — no passwords, nothing new to remember."
              : "Sign in with the Google account you use for Sourcerer."}
          </p>

          {oauthError && (
            <div className="mt-4 flex items-start gap-2 rounded-md border border-danger/40 bg-danger/10 px-3.5 py-2.5 text-xs leading-relaxed text-danger">
              <AlertCircle className="mt-0.5 size-3.5 shrink-0" />
              Sign-in didn&apos;t complete. Please try again.
            </div>
          )}

          <a
            href={loginUrl}
            className="mt-6 flex w-full items-center justify-center gap-2.5 rounded-md border border-border bg-surface-2/80 py-3 text-sm font-semibold transition-colors duration-100 hover:border-border-strong hover:bg-surface-2"
          >
            <GoogleMark />
            Continue with Google
          </a>

          <p className="mt-5 text-center text-xs text-faint">
            {isSignup ? "Already have access?" : "New here?"}{" "}
            <Link
              href={isSignup ? "/signin" : "/signup"}
              className="text-accent hover:underline"
            >
              {isSignup ? "Sign in" : "Get access"}
            </Link>
          </p>
        </motion.div>

        <p className="mt-5 text-center text-[11px] leading-relaxed text-faint">
          After signing in you can browse the index and request access — the
          library owner approves every request.
        </p>
      </div>
    </div>
  );
}

export default function AuthCard({ mode }: { mode: "signin" | "signup" }) {
  return (
    <Suspense>
      <AuthCardInner mode={mode} />
    </Suspense>
  );
}
