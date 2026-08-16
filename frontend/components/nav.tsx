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
  Home,
  LogIn,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import { useLogout, useMe } from "@/components/portal/use-me";

interface NavItem {
  href: string;
  label: string;
  icon: typeof Home;
  soon?: boolean;
}

// Admin sees the full workbench; participants get the portal surface with
// upcoming features visible but marked. RAG features ship after the beta.
const adminItems: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/resources", label: "Resources", icon: FolderLock },
  { href: "/chat", label: "Chat", icon: MessagesSquare },
  { href: "/quiz", label: "Quiz", icon: BrainCircuit },
  { href: "/ingestion", label: "Ingestion", icon: FolderInput },
  { href: "/admin", label: "Admin", icon: ShieldCheck },
];

const userItems: NavItem[] = [
  { href: "/home", label: "Home", icon: Home },
  { href: "/resources", label: "Resources", icon: FolderLock },
  { href: "/chat", label: "Chat", icon: MessagesSquare, soon: true },
  { href: "/quiz", label: "Quiz", icon: BrainCircuit, soon: true },
];

export default function Nav() {
  const pathname = usePathname();
  const { data: me } = useMe();
  const logout = useLogout();
  const navItems = me?.is_admin ? adminItems : userItems;

  return (
    <aside className="fixed left-0 top-0 z-20 flex h-screen w-60 flex-col border-r border-border bg-surface">
      <Link href={me ? "/home" : "/"} className="flex items-center gap-2.5 px-5 py-5">
        <span className="grid size-8 place-items-center rounded-md bg-accent-2">
          <Sparkles className="size-4.5 text-white" />
        </span>
        <span className="text-[17px] font-semibold tracking-tight text-text">
          Sourcerer
        </span>
      </Link>

      <nav className="mt-1 flex flex-col gap-0.5 px-3">
        {navItems.map(({ href, label, icon: Icon, soon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={`group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-100 ${
                active
                  ? "bg-white/[0.07] text-text"
                  : soon
                    ? "text-faint hover:bg-white/[0.03] hover:text-muted"
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
              {soon && (
                <span className="ml-auto rounded-full bg-white/[0.06] px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.12em] text-faint">
                  Soon
                </span>
              )}
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
          <Link
            href="/signin"
            className="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium text-muted transition-colors duration-100 hover:bg-white/[0.04] hover:text-text"
          >
            <LogIn className="size-4.5 text-faint" /> Sign in
          </Link>
        )}
      </div>
    </aside>
  );
}
