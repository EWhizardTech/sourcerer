"use client";

import { motion } from "framer-motion";
import { ArrowLeft, type LucideIcon } from "lucide-react";
import Link from "next/link";

/** Participant-facing placeholder for features that ship after the beta. */
export default function ComingSoon({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div className="grid min-h-[80vh] place-items-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="glass max-w-md p-10 text-center"
      >
        <span className="mx-auto grid size-14 place-items-center rounded-xl bg-accent-2/15 ring-1 ring-accent/25">
          <Icon className="size-7 text-accent" />
        </span>
        <div className="mt-5 flex items-center justify-center gap-2.5">
          <h1 className="text-xl font-semibold">{title}</h1>
          <span className="rounded-full bg-accent/15 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-accent ring-1 ring-accent/25">
            Coming soon
          </span>
        </div>
        <p className="mt-2.5 text-sm leading-relaxed text-muted">
          {description}
        </p>
        <Link
          href="/resources"
          className="mt-6 inline-flex items-center gap-2 rounded-md border border-border px-5 py-2.5 text-sm font-medium text-muted transition-colors duration-100 hover:border-border-strong hover:text-text"
        >
          <ArrowLeft className="size-4" /> Back to the library
        </Link>
      </motion.div>
    </div>
  );
}
