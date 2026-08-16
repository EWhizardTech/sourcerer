"use client";

/** File viewers. PDFs render to plain canvases (no text layer, per the
 * protection requirement) with the viewer's email baked into each bitmap. */

import { Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchContent } from "@/lib/portal-api";

/* ---------- PDF (canvas-only, watermark baked into bitmap) ---------- */

function drawWatermark(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  label: string
) {
  ctx.save();
  ctx.globalAlpha = 0.05;
  ctx.fillStyle = "#000";
  ctx.font = `${Math.max(14, width / 42)}px monospace`;
  ctx.translate(width / 2, height / 2);
  ctx.rotate(-Math.PI / 7);
  ctx.textAlign = "center";
  for (let y = -height; y < height; y += height / 4) {
    ctx.fillText(label, 0, y);
  }
  ctx.restore();
}

export function PdfCanvasViewer({
  url,
  email,
}: {
  url: string;
  email: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    let cancelled = false;
    const container = containerRef.current;

    (async () => {
      try {
        const pdfjs = await import("pdfjs-dist");
        // Served from /public: bundler-independent (the new URL(...) worker
        // trick breaks under the Next dev bundler with ".U is not a constructor").
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

        const resp = await fetchContent(url);
        const data = await resp.arrayBuffer();
        if (cancelled) return;

        const doc = await pdfjs.getDocument({ data }).promise;
        if (cancelled || !container) return;
        container.replaceChildren();
        setState("ready");

        const label = `${email} · Sourcerer`;
        const targetWidth = Math.min(container.clientWidth - 8, 1100);

        for (let pageNo = 1; pageNo <= doc.numPages; pageNo++) {
          if (cancelled) return;
          const page = await doc.getPage(pageNo);
          const baseViewport = page.getViewport({ scale: 1 });
          const scale = (targetWidth / baseViewport.width) * (window.devicePixelRatio || 1);
          const viewport = page.getViewport({ scale });

          const canvas = document.createElement("canvas");
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          canvas.style.width = `${viewport.width / (window.devicePixelRatio || 1)}px`;
          canvas.className = "mx-auto mb-4 rounded-lg shadow-lg";
          container.appendChild(canvas);

          const ctx = canvas.getContext("2d")!;
          await page.render({ canvasContext: ctx, viewport }).promise;
          drawWatermark(ctx, canvas.width, canvas.height, label);
        }
      } catch (err) {
        if (!cancelled) {
          setState("error");
          setDetail(err instanceof Error ? err.message : String(err));
        }
      }
    })();

    return () => {
      cancelled = true;
      container?.replaceChildren();
    };
  }, [url, email]);

  return (
    <div>
      {state === "loading" && (
        <div className="grid h-64 place-items-center text-muted">
          <span className="flex items-center gap-2">
            <Loader2 className="size-5 animate-spin" /> Rendering document…
          </span>
        </div>
      )}
      {state === "error" && (
        <div className="glass p-6 text-sm text-danger">
          Could not render document: {detail}
        </div>
      )}
      <div ref={containerRef} />
    </div>
  );
}

/* ---------- Text-based viewers ---------- */

function useTextContent(url: string) {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    fetchContent(url)
      .then((resp) => resp.text())
      .then((body) => !cancelled && setText(body))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [url]);
  return { text, error };
}

export function MarkdownViewer({ url }: { url: string }) {
  const { text, error } = useTextContent(url);
  if (error) return <div className="glass p-6 text-sm text-danger">{error}</div>;
  if (text === null)
    return <div className="p-6 text-muted">Loading…</div>;
  return (
    <div className="glass prose-chat max-w-none p-8">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

export function TextViewer({ url }: { url: string }) {
  const { text, error } = useTextContent(url);
  if (error) return <div className="glass p-6 text-sm text-danger">{error}</div>;
  if (text === null)
    return <div className="p-6 text-muted">Loading…</div>;
  return (
    <pre className="glass overflow-x-auto p-6 font-mono text-[13px] leading-relaxed text-text">
      {text}
    </pre>
  );
}

/* ---------- Image / video ---------- */

export function ImageViewer({ url, name }: { url: string; name: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchContent(url)
      .then((resp) => resp.blob())
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [url]);

  if (error) return <div className="glass p-6 text-sm text-danger">{error}</div>;
  if (!src) return <div className="p-6 text-muted">Loading…</div>;
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={name}
      draggable={false}
      className="mx-auto max-h-[80vh] max-w-full rounded-xl"
    />
  );
}

export function VideoViewer({ url }: { url: string }) {
  return (
    <video
      src={url}
      controls
      controlsList="nodownload noremoteplayback"
      disablePictureInPicture
      // no crossOrigin: media requests send cookies by default, and Chrome's
      // credentialed-CORS media path stalls without ever issuing the request
      className="mx-auto max-h-[80vh] w-full max-w-4xl rounded-xl bg-black"
    />
  );
}
