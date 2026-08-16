"use client";

import { motion } from "framer-motion";
import {
  ArrowRight,
  Eye,
  FolderLock,
  Network,
  ShieldCheck,
  Sparkles,
  Timer,
} from "lucide-react";
import Link from "next/link";
import { BetaBadge } from "@/components/app-shell";
import { useMe } from "@/components/portal/use-me";

const FEATURES = [
  {
    icon: Timer,
    title: "Timed access",
    text: "Request exactly the folders and files you need. The owner grants access for a set period — no link-sharing, no leaks.",
  },
  {
    icon: Eye,
    title: "Read everything in-app",
    text: "PDFs, slides, notes, images and lectures render right here. Nothing to download, nothing to install.",
  },
  {
    icon: Network,
    title: "A connected library",
    text: "Browse nine semesters as a tree or an interactive graph — notes link to notes, the way knowledge actually connects.",
  },
];

export default function LandingPage() {
  const { data: me } = useMe();

  return (
    <div className="flex min-h-screen flex-col">
      {/* Top bar */}
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-md bg-accent-2">
            <Sparkles className="size-4.5 text-white" />
          </span>
          <span className="text-[17px] font-semibold tracking-tight">
            Sourcerer
          </span>
          <BetaBadge />
        </div>
        <nav className="flex items-center gap-2">
          {me ? (
            <Link
              href="/home"
              className="btn-primary rounded-md px-4 py-2 text-sm font-semibold text-white"
            >
              Open library
            </Link>
          ) : (
            <>
              <Link
                href="/signin"
                className="rounded-md px-4 py-2 text-sm font-medium text-muted transition-colors duration-100 hover:text-text"
              >
                Sign in
              </Link>
              <Link
                href="/signup"
                className="btn-primary rounded-md px-4 py-2 text-sm font-semibold text-white"
              >
                Get access
              </Link>
            </>
          )}
        </nav>
      </header>

      {/* Hero */}
      <section className="mx-auto w-full max-w-6xl px-6 pb-20 pt-24 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="mx-auto max-w-3xl text-[44px] font-semibold leading-[1.05] tracking-[-1.2px] sm:text-[60px]"
        >
          Nine semesters of knowledge,
          <br />
          <span className="gradient-text">one careful library.</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.08 }}
          className="mx-auto mt-6 max-w-xl text-[17px] leading-relaxed text-muted"
        >
          Sourcerer is the front door to a curated academic archive — course
          notes, papers, slides and lectures. Sign in, request what you need,
          and read it all right here.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.16 }}
          className="mt-9 flex items-center justify-center gap-3"
        >
          <Link
            href={me ? "/home" : "/signup"}
            className="btn-primary group flex items-center gap-2 rounded-md px-6 py-3 text-sm font-semibold text-white"
          >
            {me ? "Open your library" : "Get access"}
            <ArrowRight className="size-4 transition-transform duration-100 group-hover:translate-x-0.5" />
          </Link>
          <Link
            href="/resources"
            className="rounded-md border border-border px-6 py-3 text-sm font-medium text-muted transition-colors duration-100 hover:border-border-strong hover:text-text"
          >
            Browse the index
          </Link>
        </motion.div>
      </section>

      {/* Features */}
      <section className="mx-auto w-full max-w-5xl px-6 pb-24">
        <div className="grid gap-4 md:grid-cols-3">
          {FEATURES.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.2 + i * 0.06 }}
              className="glass p-6 text-left"
            >
              <span className="grid size-10 place-items-center rounded-md bg-accent-2/15 ring-1 ring-accent/25">
                <feature.icon className="size-5 text-accent" />
              </span>
              <h2 className="mt-4 font-semibold">{feature.title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">
                {feature.text}
              </p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.45 }}
          className="mt-10 flex items-center justify-center gap-2 text-xs text-faint"
        >
          <ShieldCheck className="size-3.5" />
          Content is watermarked per viewer and served read-only — the library
          stays the owner&apos;s.
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-border">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-5 text-xs text-faint">
          <span className="flex items-center gap-2">
            <FolderLock className="size-3.5" /> Sourcerer — a private academic
            library
          </span>
          <span>Beta · access by request</span>
        </div>
      </footer>
    </div>
  );
}
