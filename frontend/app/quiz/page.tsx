"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  BrainCircuit,
  Check,
  X,
  RotateCcw,
  Trophy,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { generateQuiz, type QuizItem } from "@/lib/api";

type Phase = "setup" | "loading" | "playing" | "results";

const DIFFICULTY_STYLE: Record<string, string> = {
  Easy: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  Medium: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
  Hard: "bg-rose-500/15 text-rose-300 ring-rose-500/30",
};

export default function QuizPage() {
  const [phase, setPhase] = useState<Phase>("setup");
  const [error, setError] = useState<string | null>(null);

  // setup form
  const [query, setQuery] = useState("");
  const [courseCode, setCourseCode] = useState("");
  const [year, setYear] = useState("");
  const [tags, setTags] = useState("");
  const [numQuestions, setNumQuestions] = useState(5);

  // game state
  const [items, setItems] = useState<QuizItem[]>([]);
  const [index, setIndex] = useState(0);
  const [picked, setPicked] = useState<string | null>(null);
  const [answers, setAnswers] = useState<(string | null)[]>([]);

  const score = useMemo(
    () => answers.filter((a, i) => a === items[i]?.answer).length,
    [answers, items]
  );

  const start = async (e: React.FormEvent) => {
    e.preventDefault();
    setPhase("loading");
    setError(null);
    try {
      const quiz = await generateQuiz({
        query,
        course_code: courseCode || undefined,
        year: year || undefined,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        num_questions: numQuestions,
      });
      if (!quiz.length) throw new Error("No questions could be generated.");
      setItems(quiz);
      setAnswers([]);
      setIndex(0);
      setPicked(null);
      setPhase("playing");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Quiz generation failed");
      setPhase("setup");
    }
  };

  const confirm = () => {
    if (picked === null) return;
    setAnswers((prev) => [...prev, picked]);
  };

  const next = () => {
    setPicked(null);
    if (index + 1 >= items.length) setPhase("results");
    else setIndex(index + 1);
  };

  const restart = () => {
    setPhase("setup");
    setItems([]);
    setAnswers([]);
    setIndex(0);
    setPicked(null);
  };

  const answered = answers.length > index;
  const current = items[index];

  return (
    <div className="mx-auto max-w-3xl px-8 py-12">
      <h1 className="flex items-center gap-3 text-3xl font-bold tracking-tight">
        <span className="grid size-11 place-items-center rounded-xl bg-gradient-to-br from-violet-600/30 to-cyan-600/20 ring-1 ring-violet-500/30">
          <BrainCircuit className="size-6 text-violet-300" />
        </span>
        Quiz <span className="gradient-text">Generator</span>
      </h1>

      <AnimatePresence mode="wait">
        {/* ---------- SETUP ---------- */}
        {phase === "setup" && (
          <motion.form
            key="setup"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            onSubmit={start}
            className="glass mt-8 space-y-5 p-7"
          >
            {error && (
              <div className="rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">
                {error}
              </div>
            )}
            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted">
                Topic / query *
              </label>
              <textarea
                required
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. what is information retrieval?"
                rows={3}
                className="w-full resize-none rounded-xl border border-border bg-surface-2/80 px-4 py-3 text-sm outline-none transition focus:border-violet-500/60 focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)]"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted">
                  Course code
                </label>
                <input
                  value={courseCode}
                  onChange={(e) => setCourseCode(e.target.value)}
                  placeholder="20XW81"
                  className="w-full rounded-xl border border-border bg-surface-2/80 px-4 py-2.5 text-sm outline-none transition focus:border-violet-500/60"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted">
                  Year
                </label>
                <input
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                  placeholder="2026"
                  className="w-full rounded-xl border border-border bg-surface-2/80 px-4 py-2.5 text-sm outline-none transition focus:border-violet-500/60"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted">
                  Tags (comma-separated)
                </label>
                <input
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="retrieval, embeddings"
                  className="w-full rounded-xl border border-border bg-surface-2/80 px-4 py-2.5 text-sm outline-none transition focus:border-violet-500/60"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted">
                  Questions: {numQuestions}
                </label>
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={numQuestions}
                  onChange={(e) => setNumQuestions(Number(e.target.value))}
                  className="mt-3 w-full accent-violet-500"
                />
              </div>
            </div>
            <button
              type="submit"
              className="btn-primary w-full rounded-xl py-3 text-sm font-semibold text-white"
            >
              Generate quiz
            </button>
          </motion.form>
        )}

        {/* ---------- LOADING ---------- */}
        {phase === "loading" && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="glass mt-8 flex flex-col items-center gap-4 p-16"
          >
            <Loader2 className="size-8 animate-spin text-violet-400" />
            <p className="text-sm text-muted">
              Retrieving content and generating questions…
            </p>
            <p className="text-xs text-muted/60">
              T5 question generation + distractor mining — this can take a minute.
            </p>
          </motion.div>
        )}

        {/* ---------- PLAYING ---------- */}
        {phase === "playing" && current && (
          <motion.div
            key={`q-${index}`}
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            className="mt-8"
          >
            {/* progress */}
            <div className="mb-4 flex items-center justify-between text-xs text-muted">
              <span>
                Question {index + 1} of {items.length}
              </span>
              <span>
                Score: {score}/{answers.length}
              </span>
            </div>
            <div className="mb-6 h-1.5 overflow-hidden rounded-full bg-white/10">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-400"
                animate={{ width: `${((index + (answered ? 1 : 0)) / items.length) * 100}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>

            <div className="glass p-7">
              <div className="flex items-start justify-between gap-4">
                <h2 className="text-lg font-semibold leading-relaxed">
                  {current.question}
                </h2>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ring-1 ${
                    DIFFICULTY_STYLE[current.difficulty] ??
                    DIFFICULTY_STYLE.Medium
                  }`}
                >
                  {current.difficulty}
                </span>
              </div>

              <div className="mt-6 space-y-2.5">
                {current.options.map((option) => {
                  const isPicked = picked === option;
                  const isCorrect = option === current.answer;
                  let style =
                    "border-border hover:border-violet-500/50 hover:bg-white/5";
                  if (answered) {
                    if (isCorrect)
                      style = "border-success/60 bg-success/10 text-success";
                    else if (isPicked)
                      style = "border-danger/60 bg-danger/10 text-danger";
                    else style = "border-border opacity-50";
                  } else if (isPicked) {
                    style =
                      "border-violet-500/70 bg-violet-600/15 shadow-[0_0_0_3px_rgba(139,92,246,0.12)]";
                  }
                  return (
                    <button
                      key={option}
                      disabled={answered}
                      onClick={() => setPicked(option)}
                      className={`flex w-full items-center justify-between rounded-xl border px-4.5 py-3.5 text-left text-sm transition-all ${style}`}
                    >
                      {option}
                      {answered && isCorrect && <Check className="size-4" />}
                      {answered && isPicked && !isCorrect && (
                        <X className="size-4" />
                      )}
                    </button>
                  );
                })}
              </div>

              <div className="mt-6 flex justify-end">
                {!answered ? (
                  <button
                    onClick={confirm}
                    disabled={picked === null}
                    className="btn-primary rounded-xl px-6 py-2.5 text-sm font-semibold text-white"
                  >
                    Check answer
                  </button>
                ) : (
                  <button
                    onClick={next}
                    className="btn-primary flex items-center gap-1.5 rounded-xl px-6 py-2.5 text-sm font-semibold text-white"
                  >
                    {index + 1 >= items.length ? "See results" : "Next"}
                    <ChevronRight className="size-4" />
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}

        {/* ---------- RESULTS ---------- */}
        {phase === "results" && (
          <motion.div
            key="results"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-8"
          >
            <div className="glass flex flex-col items-center p-10 text-center">
              <motion.span
                initial={{ rotate: -12, scale: 0.6 }}
                animate={{ rotate: 0, scale: 1 }}
                transition={{ type: "spring", stiffness: 200 }}
                className="grid size-16 place-items-center rounded-2xl bg-gradient-to-br from-amber-500/30 to-violet-600/20 ring-1 ring-amber-500/40"
              >
                <Trophy className="size-8 text-amber-300" />
              </motion.span>
              <h2 className="mt-5 text-3xl font-bold">
                {score}/{items.length}
              </h2>
              <p className="mt-1 text-sm text-muted">
                {score === items.length
                  ? "Perfect score — flawless!"
                  : score >= items.length * 0.7
                    ? "Great work!"
                    : score >= items.length * 0.4
                      ? "Not bad — review the misses below."
                      : "Tough one. Review and retry!"}
              </p>
              <button
                onClick={restart}
                className="btn-primary mt-6 flex items-center gap-2 rounded-xl px-6 py-2.5 text-sm font-semibold text-white"
              >
                <RotateCcw className="size-4" /> New quiz
              </button>
            </div>

            <div className="mt-6 space-y-3">
              {items.map((item, i) => {
                const correct = answers[i] === item.answer;
                return (
                  <div
                    key={i}
                    className={`glass border-l-2 p-5 ${
                      correct ? "border-l-success" : "border-l-danger"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span
                        className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full ${
                          correct
                            ? "bg-success/20 text-success"
                            : "bg-danger/20 text-danger"
                        }`}
                      >
                        {correct ? (
                          <Check className="size-3" />
                        ) : (
                          <X className="size-3" />
                        )}
                      </span>
                      <div className="text-sm">
                        <p className="font-medium">{item.question}</p>
                        {!correct && (
                          <p className="mt-1 text-danger">
                            Your answer: {answers[i] ?? "—"}
                          </p>
                        )}
                        <p className="mt-1 text-success">
                          Correct: {item.answer}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
