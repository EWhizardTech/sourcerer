"use client";

/**
 * Aggressive-tier content protection wrapper. Deterrence, not DRM:
 * OS-level screenshots cannot be blocked by a web page — this layer makes
 * casual extraction inconvenient and every leak traceable (viewer watermark).
 *
 * - Tiled per-viewer watermark overlay (email + date)
 * - Right-click / drag / text-selection suppressed
 * - Clipboard copy truncated to ~2 sentences with attribution
 * - Print blanked (CSS + beforeprint)
 * - Content blurred while the tab/window loses focus
 * - DevTools-open heuristic hides content while open
 */

import { EyeOff, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

const COPY_SENTENCE_LIMIT = 2;

function truncateToSentences(text: string, limit: number): string {
  const matches = text.match(/[^.!?\n]+[.!?\n]?/g) ?? [];
  if (matches.length <= limit) return text;
  return matches.slice(0, limit).join("").trim();
}

export function watermarkDataUrl(label: string): string {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='420' height='280'>
    <text x='50%' y='50%' fill='rgba(255,255,255,0.055)' font-size='17'
      font-family='monospace' text-anchor='middle'
      transform='rotate(-27 210 140)'>${label}</text>
  </svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}

export default function ProtectedContent({
  email,
  children,
}: {
  email: string;
  children: React.ReactNode;
}) {
  const [veiled, setVeiled] = useState(false);
  const [devtools, setDevtools] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const watermark = useMemo(() => {
    const label = `${email} · ${new Date().toISOString().slice(0, 10)} · Sourcerer`;
    return watermarkDataUrl(label);
  }, [email]);

  useEffect(() => {
    const onVisibility = () => setVeiled(document.visibilityState !== "visible");
    const onBlur = () => setVeiled(true);
    const onFocus = () => setVeiled(false);

    const onCopy = (event: ClipboardEvent) => {
      const selection = window.getSelection()?.toString() ?? "";
      if (!selection) return;
      event.preventDefault();
      const clipped = truncateToSentences(selection, COPY_SENTENCE_LIMIT);
      event.clipboardData?.setData(
        "text/plain",
        `${clipped}… (copy limited — via Sourcerer, ${email})`
      );
    };

    const onBeforePrint = () => setVeiled(true);
    const onAfterPrint = () => setVeiled(false);

    // DevTools heuristic: docked devtools shrink the inner viewport.
    const devtoolsTimer = window.setInterval(() => {
      const open =
        window.outerWidth - window.innerWidth > 200 ||
        window.outerHeight - window.innerHeight > 220;
      setDevtools(open);
    }, 1200);

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", onBlur);
    window.addEventListener("focus", onFocus);
    document.addEventListener("copy", onCopy);
    window.addEventListener("beforeprint", onBeforePrint);
    window.addEventListener("afterprint", onAfterPrint);
    return () => {
      window.clearInterval(devtoolsTimer);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("copy", onCopy);
      window.removeEventListener("beforeprint", onBeforePrint);
      window.removeEventListener("afterprint", onAfterPrint);
    };
  }, [email]);

  return (
    <div
      ref={rootRef}
      className="protected-root relative"
      onContextMenu={(event) => event.preventDefault()}
      onDragStart={(event) => event.preventDefault()}
      style={{ userSelect: "none", WebkitUserSelect: "none" }}
    >
      <style>{`@media print { .protected-root { display: none !important; } }`}</style>

      {devtools ? (
        <div className="glass grid min-h-[50vh] place-items-center p-10 text-center">
          <div>
            <ShieldAlert className="mx-auto mb-3 size-8 text-warning" />
            <p className="font-medium">Content hidden while developer tools are open.</p>
            <p className="mt-1 text-sm text-muted">Close DevTools to continue reading.</p>
          </div>
        </div>
      ) : (
        <div
          className={`relative transition-all duration-200 ${
            veiled ? "pointer-events-none opacity-30 blur-xl" : ""
          }`}
        >
          {children}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 z-10 select-none"
            style={{ backgroundImage: watermark }}
          />
        </div>
      )}

      {veiled && !devtools && (
        <div className="absolute inset-0 z-20 grid place-items-center">
          <div className="glass flex items-center gap-2 px-5 py-3 text-sm text-muted">
            <EyeOff className="size-4" /> Content hidden — return to this tab
          </div>
        </div>
      )}
    </div>
  );
}
