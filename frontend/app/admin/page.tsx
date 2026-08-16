"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Activity,
  Check,
  Loader2,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Timer,
  X,
} from "lucide-react";
import { useState } from "react";
import { useMe } from "@/components/portal/use-me";
import {
  AdminRequest,
  adminApprove,
  adminAudit,
  adminDeny,
  adminListGrants,
  adminListRequests,
  adminPatchGrant,
  adminRevokeGrant,
  adminSyncStatus,
  adminTriggerSync,
} from "@/lib/portal-api";

function toDateInput(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

function ApproveModal({
  request,
  onClose,
}: {
  request: AdminRequest;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const defaultExpiry = new Date(
    Date.now() + request.requested_days * 86_400_000
  );
  const [expires, setExpires] = useState(defaultExpiry.toISOString().slice(0, 10));
  const [keep, setKeep] = useState<Set<string>>(
    new Set(request.items.map((item) => item.node_id))
  );

  const approve = useMutation({
    mutationFn: () =>
      adminApprove(request.id, {
        expires_at: new Date(`${expires}T23:59:59Z`).toISOString(),
        node_ids: [...keep],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-requests"] });
      queryClient.invalidateQueries({ queryKey: ["admin-grants"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass w-full max-w-lg p-6"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Approve request</h2>
          <button onClick={onClose} className="text-muted hover:text-white">
            <X className="size-5" />
          </button>
        </div>
        <p className="mt-1 text-sm text-muted">
          {request.user.name ?? request.user.email} · asked for{" "}
          {request.requested_days} days
        </p>

        <ul className="mt-4 max-h-44 space-y-1.5 overflow-y-auto">
          {request.items.map((item) => (
            <li key={item.node_id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={keep.has(item.node_id)}
                onChange={() =>
                  setKeep((prev) => {
                    const next = new Set(prev);
                    if (next.has(item.node_id)) next.delete(item.node_id);
                    else next.add(item.node_id);
                    return next;
                  })
                }
                className="size-3.5 accent-violet-500"
              />
              <span className="truncate text-muted">
                {item.is_folder ? "📁" : "📄"} {item.path ?? item.name}
              </span>
            </li>
          ))}
        </ul>

        <div className="mt-5">
          <label className="text-xs font-medium uppercase tracking-wide text-muted">
            Access until
          </label>
          <input
            type="date"
            value={expires}
            min={new Date().toISOString().slice(0, 10)}
            onChange={(event) => setExpires(event.target.value)}
            className="mt-2 rounded-xl border border-border bg-surface-2/80 px-4 py-2.5 text-sm"
          />
        </div>

        {approve.isError && (
          <p className="mt-3 text-sm text-danger">
            {(approve.error as Error).message}
          </p>
        )}

        <button
          onClick={() => approve.mutate()}
          disabled={approve.isPending || keep.size === 0}
          className="btn-primary mt-5 flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold text-white"
        >
          {approve.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Check className="size-4" />
          )}
          Grant {keep.size} item{keep.size === 1 ? "" : "s"}
        </button>
      </motion.div>
    </div>
  );
}

export default function AdminPage() {
  const { data: me, isLoading: meLoading } = useMe();
  const queryClient = useQueryClient();
  const [approving, setApproving] = useState<AdminRequest | null>(null);

  const { data: pending } = useQuery({
    queryKey: ["admin-requests"],
    queryFn: () => adminListRequests("pending"),
    enabled: !!me?.is_admin,
    refetchInterval: 30_000,
  });
  const { data: grants } = useQuery({
    queryKey: ["admin-grants"],
    queryFn: () => adminListGrants("active"),
    enabled: !!me?.is_admin,
  });
  const { data: sync } = useQuery({
    queryKey: ["admin-sync"],
    queryFn: adminSyncStatus,
    enabled: !!me?.is_admin,
    refetchInterval: (query) => (query.state.data?.running ? 3_000 : 60_000),
  });
  const { data: audit } = useQuery({
    queryKey: ["admin-audit"],
    queryFn: () => adminAudit(30),
    enabled: !!me?.is_admin,
  });

  const deny = useMutation({
    mutationFn: (id: string) => adminDeny(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-requests"] }),
  });
  const revoke = useMutation({
    mutationFn: adminRevokeGrant,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-grants"] }),
  });
  const extend = useMutation({
    mutationFn: ({ id, until }: { id: string; until: string }) =>
      adminPatchGrant(id, new Date(`${until}T23:59:59Z`).toISOString()),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-grants"] }),
  });
  const triggerSync = useMutation({
    mutationFn: adminTriggerSync,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-sync"] }),
  });

  if (meLoading)
    return (
      <div className="grid min-h-[70vh] place-items-center text-muted">
        <Loader2 className="size-6 animate-spin" />
      </div>
    );

  if (!me?.is_admin)
    return (
      <div className="grid min-h-[70vh] place-items-center">
        <div className="glass max-w-md p-8 text-center">
          <ShieldAlert className="mx-auto mb-3 size-8 text-warning" />
          <p className="text-sm text-muted">
            This dashboard is for the library owner only.
          </p>
        </div>
      </div>
    );

  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="size-6 text-violet-400" />
          <h1 className="text-2xl font-bold tracking-tight">Admin</h1>
        </div>
        <div className="glass flex items-center gap-3 px-4 py-2.5 text-xs text-muted">
          <span>
            {sync?.running
              ? "Sync running…"
              : sync?.last_finished_at
                ? `Catalog: ${sync.node_count ?? "?"} nodes · synced ${new Date(sync.last_finished_at).toLocaleString()}`
                : "Catalog never synced"}
          </span>
          {sync?.last_error && (
            <span className="text-danger">({sync.last_error})</span>
          )}
          <button
            onClick={() => triggerSync.mutate()}
            disabled={sync?.running || triggerSync.isPending}
            className="flex items-center gap-1.5 rounded-lg bg-violet-600/20 px-3 py-1.5 font-medium text-violet-300 transition-colors hover:bg-violet-600/30 disabled:opacity-40"
          >
            <RefreshCw
              className={`size-3.5 ${sync?.running ? "animate-spin" : ""}`}
            />
            Sync now
          </button>
        </div>
      </div>

      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-8"
      >
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
          Pending requests ({pending?.requests.length ?? 0})
        </h2>
        {pending?.requests.length ? (
          <div className="space-y-3">
            {pending.requests.map((request) => (
              <div key={request.id} className="glass px-5 py-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="font-medium">
                    {request.user.name ?? request.user.email}
                  </span>
                  <span className="text-xs text-muted">
                    {request.user.email} · {request.requested_days} days ·{" "}
                    {new Date(request.created_at).toLocaleString()}
                  </span>
                  <div className="ml-auto flex gap-2">
                    <button
                      onClick={() => setApproving(request)}
                      className="flex items-center gap-1.5 rounded-lg bg-success/15 px-3.5 py-1.5 text-xs font-medium text-success transition-colors hover:bg-success/25"
                    >
                      <Check className="size-3.5" /> Approve
                    </button>
                    <button
                      onClick={() => deny.mutate(request.id)}
                      className="flex items-center gap-1.5 rounded-lg bg-danger/15 px-3.5 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/25"
                    >
                      <X className="size-3.5" /> Deny
                    </button>
                  </div>
                </div>
                {request.message && (
                  <p className="mt-2 rounded-lg bg-white/5 px-3 py-2 text-sm italic text-muted">
                    “{request.message}”
                  </p>
                )}
                <ul className="mt-2 space-y-0.5 text-sm text-muted">
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
          <p className="glass px-5 py-6 text-sm text-muted">
            Nothing waiting for review.
          </p>
        )}
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.06 }}
        className="mt-10"
      >
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
          Active grants ({grants?.grants.length ?? 0})
        </h2>
        {grants?.grants.length ? (
          <div className="glass overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Resource</th>
                  <th className="px-4 py-3">Expires</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {grants.grants.map((grant) => (
                  <tr key={grant.id} className="border-b border-border/50">
                    <td className="max-w-40 truncate px-4 py-3">
                      {grant.user.email}
                    </td>
                    <td className="max-w-72 truncate px-4 py-3 text-muted">
                      {grant.is_folder ? "📁" : "📄"} {grant.path ?? grant.name}
                    </td>
                    <td
                      className={`whitespace-nowrap px-4 py-3 ${grant.expired ? "text-danger" : "text-muted"}`}
                    >
                      {new Date(grant.expires_at).toLocaleDateString()}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <input
                          type="date"
                          defaultValue={toDateInput(grant.expires_at)}
                          onBlur={(event) => {
                            if (
                              event.target.value &&
                              event.target.value !==
                                toDateInput(grant.expires_at)
                            )
                              extend.mutate({
                                id: grant.id,
                                until: event.target.value,
                              });
                          }}
                          className="rounded-lg border border-border bg-surface-2/80 px-2 py-1 text-xs"
                          title="Change expiry"
                        />
                        <button
                          onClick={() => revoke.mutate(grant.id)}
                          className="rounded-lg bg-danger/15 px-3 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/25"
                        >
                          Revoke
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="glass px-5 py-6 text-sm text-muted">No active grants.</p>
        )}
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12 }}
        className="mt-10"
      >
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted">
          <Activity className="size-4" /> Recent activity
        </h2>
        <div className="glass divide-y divide-border/50">
          {audit?.events.length ? (
            audit.events.map((event) => (
              <div
                key={event.id}
                className="flex items-center gap-3 px-5 py-2.5 text-xs"
              >
                <Timer className="size-3.5 shrink-0 text-muted/60" />
                <span className="font-medium text-muted">{event.event}</span>
                <span className="truncate text-muted/70">
                  {event.email ?? "system"}
                  {event.node_id ? ` · ${event.node_id}` : ""}
                </span>
                <span className="ml-auto shrink-0 text-muted/50">
                  {new Date(event.created_at).toLocaleString()}
                </span>
              </div>
            ))
          ) : (
            <p className="px-5 py-6 text-sm text-muted">No activity yet.</p>
          )}
        </div>
      </motion.section>

      {approving && (
        <ApproveModal request={approving} onClose={() => setApproving(null)} />
      )}
    </div>
  );
}
