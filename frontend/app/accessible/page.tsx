"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import FileBrowser, {
  ViewMode,
  ViewSwitcher,
} from "@/components/portal/file-browser";
import { useMe } from "@/components/portal/use-me";
import { getMyGrants } from "@/lib/portal-api";

export default function AccessiblePage() {
  const router = useRouter();
  const { data: me, isLoading: meLoading } = useMe();
  const [view, setView] = useState<ViewMode>("grid");

  useEffect(() => {
    if (!meLoading && !me) router.replace("/signin");
  }, [me, meLoading, router]);

  const { data: grants } = useQuery({
    queryKey: ["my-grants"],
    queryFn: getMyGrants,
    enabled: !!me,
  });
  const grantedPathIds = useMemo(
    () =>
      (grants?.grants ?? [])
        .map((g) => g.path_ids)
        .filter((p): p is string => !!p),
    [grants]
  );

  if (meLoading || !me)
    return (
      <div className="grid min-h-[70vh] place-items-center text-muted">
        <Loader2 className="size-6 animate-spin" />
      </div>
    );

  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="flex flex-wrap items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-2xl font-medium tracking-[-0.02em]">
            Accessible
          </h1>
          <p className="mt-1 text-sm text-muted">
            {me.is_admin
              ? "You own the library — everything here opens for you."
              : "The folders and files you currently have access to."}
          </p>
        </div>
        <ViewSwitcher view={view} onChange={setView} />
      </motion.div>

      <div className="mt-6">
        <FileBrowser
          rootLabel="Accessible"
          accessibleOnly
          grantedPathIds={grantedPathIds}
          isAdmin={me.is_admin}
          view={view}
        />
      </div>
    </div>
  );
}
