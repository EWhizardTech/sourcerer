"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  FolderInput,
  Loader2,
  FileText,
  Info,
  CheckCircle2,
} from "lucide-react";
import { ingestGdrive, type IngestedFile } from "@/lib/api";

export default function IngestionPage() {
  const [folderId, setFolderId] = useState("");
  const [courseCode, setCourseCode] = useState("");
  const [year, setYear] = useState("");
  const [includeRoot, setIncludeRoot] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<IngestedFile[] | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setFiles(null);
    try {
      const result = await ingestGdrive({
        folder_id: folderId.trim(),
        course_code: courseCode || undefined,
        year: year || undefined,
        include_root_as_tag: includeRoot,
      });
      setFiles(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingestion failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-8 py-12">
      <h1 className="flex items-center gap-3 text-3xl font-medium tracking-[-0.02em]">
        <span className="grid size-11 place-items-center rounded-xl bg-accent-2/15 ring-1 ring-accent/25">
          <FolderInput className="size-6 text-accent" />
        </span>
        Document <span className="gradient-text">Ingestion</span>
      </h1>
      <p className="mt-3 text-sm text-muted">
        Pull a Google Drive folder through the pipeline: parse → chunk → tag →
        embed → index. Files are processed asynchronously by the worker after
        submission.
      </p>

      <motion.form
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        onSubmit={submit}
        className="glass mt-8 space-y-5 p-7"
      >
        {error && (
          <div className="rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">
            {error}
          </div>
        )}
        <div>
          <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted">
            Google Drive folder ID *
          </label>
          <input
            required
            value={folderId}
            onChange={(e) => setFolderId(e.target.value)}
            placeholder="1AbCdEfGhIjKlMnOpQrStUvWxYz…"
            className="w-full rounded-xl border border-border bg-surface-2/80 px-4 py-3 font-mono text-sm outline-none transition focus:border-accent/60 focus:shadow-[0_0_0_3px_rgba(167,139,250,0.15)]"
          />
          <p className="mt-1.5 flex items-center gap-1 text-[11px] text-muted/70">
            <Info className="size-3" />
            The part after /folders/ in the Drive URL. The service account needs
            read access.
          </p>
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
              className="w-full rounded-xl border border-border bg-surface-2/80 px-4 py-2.5 text-sm outline-none transition focus:border-accent/60"
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
              className="w-full rounded-xl border border-border bg-surface-2/80 px-4 py-2.5 text-sm outline-none transition focus:border-accent/60"
            />
          </div>
        </div>
        <label className="flex cursor-pointer items-center gap-2.5 text-sm text-muted">
          <input
            type="checkbox"
            checked={includeRoot}
            onChange={(e) => setIncludeRoot(e.target.checked)}
            className="size-4 accent-accent"
          />
          Include root folder name as a tag
        </label>
        <button
          type="submit"
          disabled={busy}
          className="btn-primary flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold text-white"
        >
          {busy && <Loader2 className="size-4 animate-spin" />}
          {busy ? "Fetching files…" : "Start ingestion"}
        </button>
      </motion.form>

      {files && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-8"
        >
          <div className="mb-4 flex items-center gap-2 text-sm font-medium text-success">
            <CheckCircle2 className="size-4" />
            {files.length} file{files.length === 1 ? "" : "s"} queued for
            processing
          </div>
          <div className="space-y-2">
            {files.map((f) => (
              <div
                key={f.file_id}
                className="glass flex items-center gap-3 px-4 py-3"
              >
                <FileText className="size-4 shrink-0 text-accent" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">
                    {f.file_name}
                  </div>
                  <div className="truncate text-[11px] text-muted">
                    {f.file_path}
                  </div>
                </div>
                <span className="shrink-0 rounded-full bg-accent/12 px-2.5 py-1 text-[10px] font-medium text-accent ring-1 ring-accent/25">
                  queued
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
