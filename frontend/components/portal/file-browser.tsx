"use client";

/** Google-Drive-style browser: breadcrumbs + descend-into-folders, with
 * grid / list / graph views. Shared by the Library (full index, with
 * request-access selection) and Accessible (granted content only) pages. */

import { useQuery } from "@tanstack/react-query";
import {
  ChevronRight,
  FileText,
  Film,
  Folder,
  Image as ImageIcon,
  LayoutGrid,
  List,
  Loader2,
  Lock,
  LockOpen,
  Network,
  Presentation,
  Table2,
  Waypoints,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import ResourceGraph from "@/components/portal/resource-graph";
import { formatSize, isUnlocked } from "@/lib/format";
import { CatalogNode, MyGrant, getChildren, getMyGrants } from "@/lib/portal-api";

export type ViewMode = "grid" | "list" | "graph";

export interface Selection {
  selected: Map<string, CatalogNode>;
  toggle: (node: CatalogNode) => void;
}

interface Crumb {
  id: string;
  name: string;
}

export function fileIcon(name: string, mime: string) {
  const ext = name.includes(".") ? name.split(".").pop()!.toLowerCase() : "";
  if (mime.startsWith("image/")) return ImageIcon;
  if (mime.startsWith("video/")) return Film;
  if (mime.includes("presentation") || ext === "ppt" || ext === "pptx")
    return Presentation;
  if (mime.includes("spreadsheet") || ext === "csv" || ext === "xlsx")
    return Table2;
  return FileText;
}

export function ViewSwitcher({
  view,
  onChange,
}: {
  view: ViewMode;
  onChange: (view: ViewMode) => void;
}) {
  const options = [
    ["grid", LayoutGrid, "Grid"],
    ["list", List, "List"],
    ["graph", Waypoints, "Graph"],
  ] as const;
  return (
    <div className="glass flex p-1">
      {options.map(([key, Icon, label]) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          title={label}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors duration-100 ${
            view === key
              ? "bg-white/[0.07] text-text"
              : "text-muted hover:text-text"
          }`}
        >
          <Icon className="size-4" />
          <span className="hidden sm:inline">{label}</span>
        </button>
      ))}
    </div>
  );
}

function LockBadge({ unlocked }: { unlocked: boolean }) {
  return unlocked ? (
    <LockOpen className="size-3.5 shrink-0 text-success" />
  ) : (
    <Lock className="size-3.5 shrink-0 text-faint" />
  );
}

function SelectBox({
  node,
  selection,
  unlocked,
}: {
  node: CatalogNode;
  selection?: Selection;
  unlocked: boolean;
}) {
  if (!selection || unlocked) return null;
  return (
    <input
      type="checkbox"
      checked={selection.selected.has(node.id)}
      onChange={() => selection.toggle(node)}
      onClick={(event) => event.stopPropagation()}
      title="Add to access request"
      className="size-3.5 shrink-0 accent-accent"
    />
  );
}

export default function FileBrowser({
  rootLabel,
  accessibleOnly = false,
  selection,
  grantedPathIds,
  isAdmin,
  view,
}: {
  rootLabel: string;
  accessibleOnly?: boolean;
  selection?: Selection;
  grantedPathIds: string[];
  isAdmin: boolean;
  view: ViewMode;
}) {
  const router = useRouter();
  const [crumbs, setCrumbs] = useState<Crumb[]>([]); // empty = at the root
  const current = crumbs[crumbs.length - 1];

  // Accessible page top level: the user's granted roots. Admins see the
  // whole library (they can open everything).
  const virtualRoot = accessibleOnly && !isAdmin && !current;

  const { data: grantsData, isLoading: grantsLoading } = useQuery({
    queryKey: ["my-grants"],
    queryFn: getMyGrants,
    enabled: virtualRoot,
  });

  const folderId = current?.id ?? "root";
  const { data: childrenData, isLoading: childrenLoading } = useQuery({
    queryKey: ["catalog-children", folderId],
    queryFn: () => getChildren(folderId),
    staleTime: 5 * 60_000,
    enabled: !virtualRoot,
  });

  const unlockedFor = (pathIds: string) =>
    isAdmin || isUnlocked(pathIds, grantedPathIds);

  const openFolder = (id: string, name: string) =>
    setCrumbs((prev) => [...prev, { id, name }]);

  const openItem = (node: CatalogNode, unlocked: boolean) => {
    if (node.is_folder) openFolder(node.id, node.name);
    else if (unlocked) router.push(`/resources/view/${node.id}`);
    else selection?.toggle(node);
  };

  const grantNodes: CatalogNode[] = (grantsData?.grants ?? [])
    .filter((grant): grant is MyGrant & { path_ids: string } => !!grant.path_ids)
    .map((grant) => ({
      id: grant.node_id,
      parent_id: null,
      name: grant.name,
      is_folder: grant.is_folder,
      mime_type: grant.is_folder ? "application/vnd.google-apps.folder" : "",
      size: null,
      modified_time: null,
      path: grant.path ?? grant.name,
      path_ids: grant.path_ids,
    }));

  const items = virtualRoot ? grantNodes : (childrenData?.children ?? []);
  const loading = virtualRoot ? grantsLoading : childrenLoading;
  const folders = items.filter((item) => item.is_folder);
  const files = items.filter((item) => !item.is_folder);

  return (
    <div>
      {/* Breadcrumbs */}
      <nav className="mb-4 flex flex-wrap items-center gap-1 text-sm">
        <button
          onClick={() => setCrumbs([])}
          className={`rounded-md px-2 py-1 transition-colors duration-100 ${
            crumbs.length
              ? "text-muted hover:bg-white/[0.05] hover:text-text"
              : "font-medium text-text"
          }`}
        >
          {rootLabel}
        </button>
        {crumbs.map((crumb, i) => (
          <span key={crumb.id} className="flex items-center gap-1">
            <ChevronRight className="size-3.5 text-faint" />
            <button
              onClick={() => setCrumbs(crumbs.slice(0, i + 1))}
              className={`max-w-48 truncate rounded-md px-2 py-1 transition-colors duration-100 ${
                i === crumbs.length - 1
                  ? "font-medium text-text"
                  : "text-muted hover:bg-white/[0.05] hover:text-text"
              }`}
            >
              {crumb.name}
            </button>
          </span>
        ))}
      </nav>

      {/* Content */}
      {view === "graph" ? (
        virtualRoot ? (
          <div className="glass grid min-h-72 place-items-center px-6 py-12 text-center">
            <div>
              <Network className="mx-auto mb-3 size-7 text-faint" />
              <p className="text-sm text-muted">
                Open one of your folders to see its graph.
              </p>
            </div>
          </div>
        ) : (
          <ResourceGraph rootId={folderId} onOpenFolder={openFolder} />
        )
      ) : loading ? (
        <div className="glass grid min-h-72 place-items-center text-muted">
          <Loader2 className="size-6 animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="glass px-6 py-14 text-center text-sm text-muted">
          {virtualRoot
            ? "Nothing unlocked yet — browse the Library and request access."
            : "This folder is empty."}
        </div>
      ) : view === "grid" ? (
        <div className="space-y-6">
          {folders.length > 0 && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {folders.map((node) => {
                const unlocked = unlockedFor(node.path_ids);
                return (
                  <button
                    key={node.id}
                    onClick={() => openItem(node, unlocked)}
                    className="glass glass-hover group flex items-center gap-3 px-4 py-3 text-left"
                  >
                    <Folder className="size-5 shrink-0 text-accent" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm">{node.name}</span>
                      <span className="block text-[11px] text-faint">
                        {node.child_count ?? 0} items
                      </span>
                    </span>
                    <LockBadge unlocked={unlocked} />
                    <SelectBox
                      node={node}
                      selection={selection}
                      unlocked={unlocked}
                    />
                  </button>
                );
              })}
            </div>
          )}
          {files.length > 0 && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {files.map((node) => {
                const unlocked = unlockedFor(node.path_ids);
                const Icon = fileIcon(node.name, node.mime_type);
                return (
                  <button
                    key={node.id}
                    onClick={() => openItem(node, unlocked)}
                    className="glass glass-hover group flex flex-col gap-3 p-4 text-left"
                  >
                    <div className="flex w-full items-center justify-between">
                      <Icon
                        className={`size-5 ${unlocked ? "text-accent" : "text-faint"}`}
                      />
                      <span className="flex items-center gap-2">
                        <LockBadge unlocked={unlocked} />
                        <SelectBox
                          node={node}
                          selection={selection}
                          unlocked={unlocked}
                        />
                      </span>
                    </div>
                    <span className="min-w-0">
                      <span
                        className={`block truncate text-sm ${unlocked ? "" : "text-muted"}`}
                      >
                        {node.name}
                      </span>
                      <span className="mt-0.5 block text-[11px] text-faint">
                        {formatSize(node.size) || "—"}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <div className="glass divide-y divide-border/60">
          {[...folders, ...files].map((node) => {
            const unlocked = unlockedFor(node.path_ids);
            const Icon = node.is_folder
              ? Folder
              : fileIcon(node.name, node.mime_type);
            return (
              <button
                key={node.id}
                onClick={() => openItem(node, unlocked)}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors duration-100 hover:bg-white/[0.04]"
              >
                <Icon
                  className={`size-4.5 shrink-0 ${
                    node.is_folder
                      ? "text-accent"
                      : unlocked
                        ? "text-accent"
                        : "text-faint"
                  }`}
                />
                <span
                  className={`min-w-0 flex-1 truncate ${unlocked || node.is_folder ? "" : "text-muted"}`}
                >
                  {node.name}
                </span>
                <span className="w-20 shrink-0 text-right text-xs text-faint">
                  {node.is_folder
                    ? `${node.child_count ?? 0} items`
                    : formatSize(node.size) || "—"}
                </span>
                <span className="flex w-16 shrink-0 items-center justify-end gap-2.5">
                  <LockBadge unlocked={unlocked} />
                  <SelectBox
                    node={node}
                    selection={selection}
                    unlocked={unlocked}
                  />
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
