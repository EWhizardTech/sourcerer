"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, Clock, Loader2, LockOpen, XCircle } from "lucide-react";
import Link from "next/link";
import { useMe } from "@/components/portal/use-me";
import {
  cancelRequest,
  getMyGrants,
  getMyRequests,
} from "@/lib/portal-api";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-warning/15 text-warning",
  approved: "bg-success/15 text-success",
  denied: "bg-danger/15 text-danger",
  cancelled: "bg-white/10 text-muted",
};

function daysLeft(expiresAt: string): string {
  const ms = new Date(expiresAt).getTime() - Date.now();
  if (ms <= 0) return "expired";
  const days = Math.floor(ms / 86_400_000);
  if (days > 0) return `${days}d left`;
  return `${Math.floor(ms / 3_600_000)}h left`;
}

export default function MyRequestsPage() {
  const { data: me, isLoading: meLoading } = useMe();
  const queryClient = useQueryClient();

  const { data: requests } = useQuery({
    queryKey: ["my-requests"],
    queryFn: getMyRequests,
    enabled: !!me,
  });
  const { data: grants } = useQuery({
    queryKey: ["my-grants"],
    queryFn: getMyGrants,
    enabled: !!me,
  });

  const cancel = useMutation({
    mutationFn: cancelRequest,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["my-requests"] }),
  });

  if (meLoading)
    return (
      <div className="grid min-h-[70vh] place-items-center text-muted">
        <Loader2 className="size-6 animate-spin" />
      </div>
    );
  if (!me)
    return (
      <div className="grid min-h-[70vh] place-items-center">
        <a
          href="/signin"
          className="btn-primary rounded-xl px-6 py-3 text-sm font-semibold text-white"
        >
          Sign in to continue
        </a>
      </div>
    );

  return (
    <div className="mx-auto max-w-4xl px-8 py-8">
      <div className="flex items-center gap-3">
        <Link
          href="/resources"
          className="glass grid size-9 place-items-center text-muted hover:text-text"
        >
          <ArrowLeft className="size-4" />
        </Link>
        <h1 className="text-2xl font-medium tracking-[-0.02em]">My access</h1>
      </div>

      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-8"
      >
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted">
          <LockOpen className="size-4 text-success" /> Active grants
        </h2>
        {grants?.grants.length ? (
          <div className="space-y-2">
            {grants.grants.map((grant) => (
              <div
                key={grant.id}
                className="glass flex items-center gap-3 px-5 py-3.5 text-sm"
              >
                <span className="truncate">
                  {grant.is_folder ? "📁" : "📄"} {grant.path ?? grant.name}
                </span>
                <span className="ml-auto shrink-0 rounded-full bg-success/15 px-3 py-1 text-xs text-success">
                  {daysLeft(grant.expires_at)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="glass px-5 py-6 text-sm text-muted">
            No active grants yet — request access from the library.
          </p>
        )}
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.06 }}
        className="mt-10"
      >
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted">
          <Clock className="size-4" /> Requests
        </h2>
        {requests?.requests.length ? (
          <div className="space-y-3">
            {requests.requests.map((request) => (
              <div key={request.id} className="glass px-5 py-4">
                <div className="flex items-center gap-3">
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_STYLES[request.status]}`}
                  >
                    {request.status}
                  </span>
                  <span className="text-xs text-muted">
                    {new Date(request.created_at).toLocaleDateString()} ·{" "}
                    {request.requested_days} days requested
                  </span>
                  {request.status === "pending" && (
                    <button
                      onClick={() => cancel.mutate(request.id)}
                      className="ml-auto flex items-center gap-1 text-xs text-muted transition-colors hover:text-danger"
                    >
                      <XCircle className="size-3.5" /> Cancel
                    </button>
                  )}
                </div>
                <ul className="mt-2.5 space-y-0.5 text-sm text-muted">
                  {request.items.map((item) => (
                    <li key={item.node_id} className="truncate">
                      {item.is_folder ? "📁" : "📄"} {item.path ?? item.name}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <p className="glass px-5 py-6 text-sm text-muted">No requests yet.</p>
        )}
      </motion.section>
    </div>
  );
}
