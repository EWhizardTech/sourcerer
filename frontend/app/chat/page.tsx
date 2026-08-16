"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Send,
  Square,
  Plus,
  Sparkles,
  FileText,
  Globe,
  ChevronDown,
} from "lucide-react";
import {
  streamChat,
  clearChatSession,
  type ChatSource,
  type ChatStreamEvent,
} from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  streaming?: boolean;
  error?: boolean;
}

const SUGGESTIONS = [
  "What is information retrieval?",
  "Explain TF-IDF with an example",
  "Summarize the key ideas of vector space models",
  "What are inverted indexes used for?",
];

function ScoreBar({ score }: { score: number | null }) {
  if (score === null || score === undefined) return null;
  // Normalize: rerank logits roughly [-12, 12], RRF scores are tiny.
  const pct = Math.max(6, Math.min(100, ((score + 12) / 24) * 100));
  return (
    <div className="h-1 w-16 overflow-hidden rounded-full bg-white/10">
      <div
        className="h-full rounded-full bg-accent"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function SourceCard({ source }: { source: ChatSource }) {
  const [open, setOpen] = useState(false);
  const Icon = source.type === "web" ? Globe : FileText;
  return (
    <div className="glass overflow-hidden !rounded-xl border-white/5">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-3.5 py-2.5 text-left transition hover:bg-white/5"
      >
        <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-accent/15 text-[11px] font-semibold text-accent ring-1 ring-accent/25">
          {source.id}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 truncate text-xs font-medium">
            <Icon className="size-3 shrink-0 text-accent" />
            <span className="truncate">{source.source}</span>
          </div>
          <div className="mt-0.5 flex items-center gap-2 text-[10px] text-muted">
            {source.page_number != null && <span>p. {source.page_number}</span>}
            {source.subject && <span>· {source.subject}</span>}
            <ScoreBar score={source.score} />
          </div>
        </div>
        <ChevronDown
          className={`size-4 shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <p className="border-t border-white/5 px-3.5 py-3 text-xs leading-relaxed text-muted">
              {source.text.length > 600
                ? source.text.slice(0, 600) + "…"
                : source.text}
            </p>
            {source.url && (
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="block border-t border-white/5 px-3.5 py-2 text-[11px] text-accent hover:underline"
              >
                {source.url}
              </a>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(
    async (text: string) => {
      const query = text.trim();
      if (!query || busy) return;

      setInput("");
      setBusy(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: query },
        { role: "assistant", content: "", streaming: true, sources: [] },
      ]);

      const controller = new AbortController();
      abortRef.current = controller;

      const patchLast = (patch: Partial<Message>) =>
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...next[next.length - 1], ...patch };
          return next;
        });

      try {
        for await (const ev of streamChat(
          query,
          sessionRef.current,
          controller.signal
        ) as AsyncGenerator<ChatStreamEvent>) {
          if (ev.event === "session") {
            sessionRef.current = ev.session_id;
          } else if (ev.event === "sources") {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = {
                ...last,
                sources: [...(last.sources ?? []), ...ev.sources],
              };
              return next;
            });
          } else if (ev.event === "token") {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = {
                ...last,
                content: last.content + ev.text,
              };
              return next;
            });
          } else if (ev.event === "done") {
            patchLast({
              content: ev.answer,
              sources: ev.sources,
              streaming: false,
            });
          } else if (ev.event === "error") {
            patchLast({
              content: `Something went wrong: ${ev.detail}`,
              streaming: false,
              error: true,
            });
          }
        }
        patchLast({ streaming: false });
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          patchLast({
            content: `Connection failed: ${(e as Error).message}`,
            streaming: false,
            error: true,
          });
        } else {
          patchLast({ streaming: false });
        }
      } finally {
        setBusy(false);
        abortRef.current = null;
      }
    },
    [busy]
  );

  const stop = () => abortRef.current?.abort();

  const newChat = async () => {
    stop();
    if (sessionRef.current) void clearChatSession(sessionRef.current);
    sessionRef.current = null;
    setMessages([]);
  };

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-8 py-4">
        <div>
          <h1 className="text-lg font-semibold">Chat</h1>
          <p className="text-xs text-muted">
            Streaming answers grounded in your knowledge base
          </p>
        </div>
        <button
          onClick={newChat}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted transition hover:border-accent/50 hover:text-text"
        >
          <Plus className="size-3.5" /> New chat
        </button>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-8 py-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center pt-24 text-center">
              <motion.span
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="grid size-16 place-items-center rounded-xl bg-accent-2/15 ring-1 ring-accent/25"
              >
                <Sparkles className="size-8 text-accent" />
              </motion.span>
              <h2 className="mt-6 text-2xl font-semibold">
                Ask your <span className="gradient-text">course material</span>
              </h2>
              <p className="mt-2 max-w-md text-sm text-muted">
                Answers stream in real time with inline citations [1] backed by
                the retrieved sources. Add &quot;search the web&quot; to pull in
                live results.
              </p>
              <div className="mt-8 grid w-full max-w-xl grid-cols-1 gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="glass glass-hover px-4 py-3 text-left text-sm text-muted hover:text-text"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) =>
            msg.role === "user" ? (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-end"
              >
                <div className="max-w-[80%] rounded-xl rounded-br-sm bg-accent-2 px-4.5 py-3 text-sm">
                  {msg.content}
                </div>
              </motion.div>
            ) : (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col gap-3"
              >
                {msg.sources && msg.sources.length > 0 && (
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {msg.sources.map((src) => (
                      <SourceCard key={`${i}-${src.chunk_id}`} source={src} />
                    ))}
                  </div>
                )}
                <div
                  className={`glass max-w-full !rounded-xl !rounded-bl-sm px-5 py-4 ${
                    msg.error ? "border-danger/40" : ""
                  }`}
                >
                  {msg.content ? (
                    <div
                      className={`prose-chat ${msg.streaming ? "stream-caret" : ""}`}
                    >
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 py-1 text-sm text-muted">
                      <span className="shimmer h-4 w-40 rounded" />
                    </div>
                  )}
                </div>
              </motion.div>
            )
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Composer */}
      <div className="border-t border-border bg-surface px-8 py-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="mx-auto flex max-w-3xl items-end gap-3"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            rows={1}
            placeholder="Ask anything about your documents…"
            className="max-h-40 min-h-[48px] flex-1 resize-none rounded-xl border border-border bg-surface-2/80 px-4 py-3 text-sm outline-none transition placeholder:text-muted/60 focus:border-accent/60 focus:shadow-[0_0_0_3px_rgba(167,139,250,0.15)]"
          />
          {busy ? (
            <button
              type="button"
              onClick={stop}
              className="grid size-12 place-items-center rounded-xl border border-danger/40 text-danger transition hover:bg-danger/10"
              title="Stop"
            >
              <Square className="size-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="btn-primary grid size-12 place-items-center rounded-xl text-white"
              title="Send"
            >
              <Send className="size-4.5" />
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
