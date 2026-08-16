"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sparkles,
  LayoutDashboard,
  MessagesSquare,
  BrainCircuit,
  FolderInput,
  FolderLock,
  ShieldCheck,
  LogOut,
} from "lucide-react";
import { useLogout, useMe } from "@/components/portal/use-me";

// Beta: the portal is the public surface; RAG features stay admin-only.
const adminItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessagesSquare },
  { href: "/quiz", label: "Quiz", icon: BrainCircuit },
  { href: "/ingestion", label: "Ingestion", icon: FolderInput },
];
const publicItems = [{ href: "/resources", label: "Resources", icon: FolderLock }];

export default function Nav() {
  const pathname = usePathname();
  const { data: me } = useMe();
  const logout = useLogout();
  const navItems = me?.is_admin
    ? [
        ...adminItems,
        ...publicItems,
        { href: "/admin", label: "Admin", icon: ShieldCheck },
      ]
    : publicItems;

  return (
    <aside className="fixed left-0 top-0 z-20 flex h-screen w-60 flex-col border-r border-border bg-surface">
      <Link href="/" className="flex items-center gap-2.5 px-5 py-5">
        <span className="grid size-8 place-items-center rounded-md bg-accent-2">
          <Sparkles className="size-4.5 text-white" />
        </span>
        <span className="text-[17px] font-semibold tracking-tight text-text">
          Sourcerer
        </span>
      </Link>

      <nav className="mt-1 flex flex-col gap-0.5 px-3">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-100 ${
                active
                  ? "bg-white/[0.07] text-text"
                  : "text-muted hover:bg-white/[0.04] hover:text-text"
              }`}
            >
              {active && (
                <span className="absolute -left-3 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-accent" />
              )}
              <Icon
                className={`size-4.5 transition-colors duration-100 ${
                  active ? "text-accent" : "text-faint group-hover:text-muted"
                }`}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto border-t border-border px-3 py-3">
        {me ? (
          <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
            {me.picture ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={me.picture}
                alt=""
                className="size-7 shrink-0 rounded-full"
                referrerPolicy="no-referrer"
              />
            ) : (
              <span className="grid size-7 shrink-0 place-items-center rounded-full bg-accent-2 text-xs font-semibold text-white">
                {me.email[0].toUpperCase()}
              </span>
            )}
            <span className="min-w-0 flex-1 truncate text-xs text-muted">
              {me.name ?? me.email}
            </span>
            <button
              onClick={() => logout()}
              title="Sign out"
              className="rounded-sm p-1 text-faint transition-colors duration-100 hover:text-danger"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        ) : (
          <div className="px-2 text-[11px] leading-relaxed text-faint">
            Your academic resource library
          </div>
        )}
      </div>
    </aside>
  );
}
