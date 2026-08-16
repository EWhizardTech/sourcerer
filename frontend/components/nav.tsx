"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sparkles,
  LayoutDashboard,
  MessagesSquare,
  BrainCircuit,
  FolderInput,
} from "lucide-react";

const items = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessagesSquare },
  { href: "/quiz", label: "Quiz", icon: BrainCircuit },
  { href: "/ingestion", label: "Ingestion", icon: FolderInput },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-20 flex h-screen w-60 flex-col border-r border-border bg-surface/60 backdrop-blur-xl">
      <Link href="/" className="flex items-center gap-2.5 px-6 py-6">
        <span className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-violet-600 to-cyan-600 shadow-lg shadow-violet-900/40">
          <Sparkles className="size-5 text-white" />
        </span>
        <span className="text-lg font-bold tracking-tight gradient-text">
          Sourcerer
        </span>
      </Link>

      <nav className="mt-2 flex flex-col gap-1 px-3">
        {items.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`group flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all ${
                active
                  ? "bg-gradient-to-r from-violet-600/25 to-cyan-600/10 text-white shadow-inner"
                  : "text-muted hover:bg-white/5 hover:text-white"
              }`}
            >
              <Icon
                className={`size-4.5 transition-colors ${
                  active ? "text-violet-400" : "text-muted group-hover:text-violet-300"
                }`}
              />
              {label}
              {active && (
                <span className="ml-auto size-1.5 rounded-full bg-gradient-to-r from-violet-400 to-cyan-400" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto px-6 py-5 text-[11px] leading-relaxed text-muted/70">
        AI-powered RAG platform
        <br />
        for educational content
      </div>
    </aside>
  );
}
