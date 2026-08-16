"use client";

import { usePathname } from "next/navigation";
import Nav from "@/components/nav";

const PUBLIC_ROUTES = new Set(["/", "/signin", "/signup"]);

export function BetaBadge() {
  return (
    <span className="rounded-full bg-accent/15 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-accent ring-1 ring-accent/25">
      Beta
    </span>
  );
}

/** Public routes (landing, sign-in/up) render bare; app routes get the
 * sidebar shell. A Beta badge floats top-right everywhere except public
 * pages, whose headers place it themselves. */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_ROUTES.has(pathname);

  if (isPublic) return <>{children}</>;

  return (
    <>
      <div className="fixed right-5 top-4 z-40">
        <BetaBadge />
      </div>
      <Nav />
      <main className="ml-60 min-h-screen">{children}</main>
    </>
  );
}
