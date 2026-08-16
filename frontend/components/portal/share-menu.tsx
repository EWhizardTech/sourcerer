"use client";

/** Share popover for a library item: copy the Sourcerer link or hand it to
 * a social app / email. Links point into Sourcerer, never at Drive — the
 * recipient still signs in and needs (or requests) access. */

import {
  Check,
  Copy,
  Mail,
  MessageCircle,
  Send,
  Share2,
  Twitter,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

export default function ShareMenu({
  url,
  title,
  className = "",
}: {
  url: string;
  title: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const rootRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const text = `${title} — on Sourcerer`;
  const encodedUrl = encodeURIComponent(url);
  const encodedText = encodeURIComponent(text);

  const copy = async () => {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => {
      setCopied(false);
      setOpen(false);
    }, 900);
  };

  const external = [
    {
      label: "WhatsApp",
      icon: MessageCircle,
      href: `https://wa.me/?text=${encodedText}%20${encodedUrl}`,
    },
    {
      label: "Telegram",
      icon: Send,
      href: `https://t.me/share/url?url=${encodedUrl}&text=${encodedText}`,
    },
    {
      label: "X",
      icon: Twitter,
      href: `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedText}`,
    },
    {
      label: "Email",
      icon: Mail,
      href: `mailto:?subject=${encodedText}&body=${encodedText}%0A${encodedUrl}`,
    },
  ];

  return (
    <span
      ref={rootRef}
      className={`relative ${className}`}
      onClick={(event) => event.stopPropagation()}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        title="Share"
        className={`rounded-sm p-1 transition-colors duration-100 ${
          open ? "text-accent" : "text-faint hover:text-text"
        }`}
      >
        <Share2 className="size-3.5" />
      </button>

      {open && (
        <div className="absolute right-0 top-7 z-30 w-44 rounded-md border border-border bg-surface p-1.5 shadow-[var(--shadow-elevated)]">
          <button
            onClick={copy}
            className="flex w-full items-center gap-2.5 rounded-sm px-2.5 py-1.5 text-left text-xs text-muted transition-colors duration-100 hover:bg-white/[0.05] hover:text-text"
          >
            {copied ? (
              <Check className="size-3.5 text-success" />
            ) : (
              <Copy className="size-3.5" />
            )}
            {copied ? "Copied!" : "Copy link"}
          </button>
          {typeof navigator !== "undefined" && "share" in navigator && (
            <button
              onClick={() => {
                navigator.share({ title: text, url }).catch(() => {});
                setOpen(false);
              }}
              className="flex w-full items-center gap-2.5 rounded-sm px-2.5 py-1.5 text-left text-xs text-muted transition-colors duration-100 hover:bg-white/[0.05] hover:text-text"
            >
              <Share2 className="size-3.5" /> Share…
            </button>
          )}
          <div className="my-1 border-t border-border/60" />
          {external.map(({ label, icon: Icon, href }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 rounded-sm px-2.5 py-1.5 text-xs text-muted transition-colors duration-100 hover:bg-white/[0.05] hover:text-text"
            >
              <Icon className="size-3.5" /> {label}
            </a>
          ))}
        </div>
      )}
    </span>
  );
}
