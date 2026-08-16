"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  MessagesSquare,
  BrainCircuit,
  FolderInput,
  RefreshCw,
  Server,
  Database,
  Zap,
  ArrowRight,
} from "lucide-react";
import { getHealth, type AggregateHealth } from "@/lib/api";

const SERVICE_META: Record<
  string,
  { label: string; blurb: string; icon: typeof Server }
> = {
  ingestion: {
    label: "Ingestion",
    blurb: "Drive intake · parse · chunk · embed",
    icon: Database,
  },
  retrieval: {
    label: "Retrieval",
    blurb: "Agentic RAG · streaming · citations",
    icon: Zap,
  },
  quiz: {
    label: "Quiz",
    blurb: "T5 question generation · NLP",
    icon: BrainCircuit,
  },
};

const ACTIONS = [
  {
    href: "/chat",
    icon: MessagesSquare,
    title: "Ask Sourcerer",
    text: "Chat with your knowledge base — streamed answers with inline citations.",
  },
  {
    href: "/quiz",
    icon: BrainCircuit,
    title: "Generate a quiz",
    text: "Turn course material into an interactive multiple-choice quiz.",
  },
  {
    href: "/ingestion",
    icon: FolderInput,
    title: "Ingest documents",
    text: "Pull a Google Drive folder through the processing pipeline.",
  },
];

function StatusDot({ status }: { status: string }) {
  const color =
    status === "ok"
      ? "text-success bg-success"
      : status === "down"
        ? "text-danger bg-danger"
        : "text-warning bg-warning";
  return (
    <span className={`dot-pulse inline-block size-2.5 rounded-full ${color}`} />
  );
}

export default function Dashboard() {
  const [health, setHealth] = useState<AggregateHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setHealth(await getHealth());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gateway unreachable");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 15000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="mx-auto max-w-5xl px-8 py-12">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-4xl font-bold tracking-tight">
          Welcome to <span className="gradient-text">Sourcerer</span>
        </h1>
        <p className="mt-3 max-w-xl text-muted">
          Retrieval-augmented answers, quizzes and ingestion over your course
          material — powered by hybrid search, reranking and grounded citations.
        </p>
      </motion.div>

      {/* System status */}
      <div className="mt-10 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-muted">
          System status
        </h2>
        <button
          onClick={refresh}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-muted transition hover:border-border-strong hover:text-white"
        >
          <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-5"
        >
          <div className="flex items-center justify-between">
            <Server className="size-5 text-violet-400" />
            <StatusDot status={error ? "down" : health ? "ok" : "..."} />
          </div>
          <div className="mt-3 font-semibold">Gateway</div>
          <div className="mt-0.5 text-xs text-muted">
            {error ? error : "Single entry point · proxy + health"}
          </div>
        </motion.div>

        {Object.entries(SERVICE_META).map(([key, meta], i) => {
          const svc = health?.services?.[key];
          const status = svc?.status ?? (error ? "down" : "…");
          return (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * (i + 1) }}
              className="glass p-5"
            >
              <div className="flex items-center justify-between">
                <meta.icon className="size-5 text-cyan-400" />
                <StatusDot status={status} />
              </div>
              <div className="mt-3 font-semibold">{meta.label}</div>
              <div className="mt-0.5 text-xs text-muted">{meta.blurb}</div>
            </motion.div>
          );
        })}
      </div>

      {/* Quick actions */}
      <h2 className="mt-12 text-sm font-semibold uppercase tracking-widest text-muted">
        Get started
      </h2>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {ACTIONS.map((action, i) => (
          <motion.div
            key={action.href}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 + 0.07 * i }}
          >
            <Link
              href={action.href}
              className="glass glass-hover group block h-full p-6"
            >
              <span className="grid size-11 place-items-center rounded-xl bg-gradient-to-br from-violet-600/30 to-cyan-600/20 ring-1 ring-violet-500/30">
                <action.icon className="size-5 text-violet-300" />
              </span>
              <div className="mt-4 flex items-center gap-2 font-semibold">
                {action.title}
                <ArrowRight className="size-4 -translate-x-1 opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" />
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">
                {action.text}
              </p>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
