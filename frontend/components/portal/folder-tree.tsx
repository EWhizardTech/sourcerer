"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ChevronRight,
  FileText,
  Film,
  Folder,
  FolderOpen,
  Image as ImageIcon,
  Lock,
  LockOpen,
  Presentation,
  Table2,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { CatalogNode, getChildren } from "@/lib/portal-api";

export function formatSize(size: number | null): string {
  if (size == null) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(0)} KB`;
  if (size < 1024 * 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function fileIcon(node: CatalogNode) {
  const ext = node.name.includes(".")
    ? node.name.split(".").pop()!.toLowerCase()
    : "";
  const mime = node.mime_type;
  if (mime.startsWith("image/")) return ImageIcon;
  if (mime.startsWith("video/")) return Film;
  if (
    mime.includes("presentation") ||
    ext === "ppt" ||
    ext === "pptx"
  )
    return Presentation;
  if (mime.includes("spreadsheet") || ext === "csv" || ext === "xlsx")
    return Table2;
  return FileText;
}

export interface TreeSelection {
  selected: Map<string, CatalogNode>;
  toggle: (node: CatalogNode) => void;
}

/** True when the node is covered by a granted path prefix. */
export function isUnlocked(pathIds: string, grantedPathIds: string[]): boolean {
  return grantedPathIds.some((prefix) => pathIds.startsWith(prefix));
}

function TreeRow({
  node,
  depth,
  selection,
  grantedPathIds,
  isAdmin,
}: {
  node: CatalogNode;
  depth: number;
  selection: TreeSelection;
  grantedPathIds: string[];
  isAdmin: boolean;
}) {
  const [open, setOpen] = useState(false);
  const unlocked = isAdmin || isUnlocked(node.path_ids, grantedPathIds);
  const checked = selection.selected.has(node.id);
  const Icon = node.is_folder ? (open ? FolderOpen : Folder) : fileIcon(node);

  return (
    <div>
      <div
        className={`group flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors hover:bg-white/5 ${
          checked ? "bg-violet-600/10" : ""
        }`}
        style={{ paddingLeft: `${depth * 1.25 + 0.5}rem` }}
      >
        {node.is_folder ? (
          <button
            onClick={() => setOpen((v) => !v)}
            className="grid size-5 shrink-0 place-items-center rounded text-muted hover:text-white"
            aria-label={open ? "Collapse" : "Expand"}
          >
            <ChevronRight
              className={`size-3.5 transition-transform ${open ? "rotate-90" : ""}`}
            />
          </button>
        ) : (
          <span className="size-5 shrink-0" />
        )}

        <input
          type="checkbox"
          checked={checked}
          onChange={() => selection.toggle(node)}
          disabled={unlocked}
          title={unlocked ? "Already accessible" : "Add to access request"}
          className="size-3.5 shrink-0 accent-violet-500 disabled:opacity-30"
        />

        <Icon
          className={`size-4 shrink-0 ${
            node.is_folder ? "text-violet-400" : "text-muted"
          }`}
        />

        {!node.is_folder && unlocked ? (
          <Link
            href={`/resources/view/${node.id}`}
            className="truncate text-text hover:text-violet-300 hover:underline"
          >
            {node.name}
          </Link>
        ) : (
          <button
            onClick={() => node.is_folder && setOpen((v) => !v)}
            className={`truncate text-left ${
              node.is_folder ? "text-text" : "text-muted"
            }`}
          >
            {node.name}
          </button>
        )}

        <span className="ml-auto flex shrink-0 items-center gap-2 text-[11px] text-muted">
          {node.is_folder ? (
            <span>{node.child_count ?? 0} items</span>
          ) : (
            <span>{formatSize(node.size)}</span>
          )}
          {unlocked ? (
            <LockOpen className="size-3.5 text-success" />
          ) : (
            <Lock className="size-3.5 text-muted/60" />
          )}
        </span>
      </div>

      {open && node.is_folder && (
        <TreeChildren
          parentId={node.id}
          depth={depth + 1}
          selection={selection}
          grantedPathIds={grantedPathIds}
          isAdmin={isAdmin}
        />
      )}
    </div>
  );
}

function TreeChildren({
  parentId,
  depth,
  selection,
  grantedPathIds,
  isAdmin,
}: {
  parentId: string;
  depth: number;
  selection: TreeSelection;
  grantedPathIds: string[];
  isAdmin: boolean;
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["catalog-children", parentId],
    queryFn: () => getChildren(parentId),
    staleTime: 5 * 60_000,
  });

  if (isLoading)
    return (
      <div
        className="py-1.5 text-xs text-muted"
        style={{ paddingLeft: `${depth * 1.25 + 1}rem` }}
      >
        Loading…
      </div>
    );
  if (error)
    return (
      <div
        className="py-1.5 text-xs text-danger"
        style={{ paddingLeft: `${depth * 1.25 + 1}rem` }}
      >
        {(error as Error).message}
      </div>
    );
  if (!data?.children.length)
    return (
      <div
        className="py-1.5 text-xs text-muted/60"
        style={{ paddingLeft: `${depth * 1.25 + 1}rem` }}
      >
        Empty folder
      </div>
    );

  return (
    <div>
      {data.children.map((child) => (
        <TreeRow
          key={child.id}
          node={child}
          depth={depth}
          selection={selection}
          grantedPathIds={grantedPathIds}
          isAdmin={isAdmin}
        />
      ))}
    </div>
  );
}

export default function FolderTree({
  selection,
  grantedPathIds,
  isAdmin,
}: {
  selection: TreeSelection;
  grantedPathIds: string[];
  isAdmin: boolean;
}) {
  return (
    <div className="glass p-3">
      <TreeChildren
        parentId="root"
        depth={0}
        selection={selection}
        grantedPathIds={grantedPathIds}
        isAdmin={isAdmin}
      />
    </div>
  );
}
