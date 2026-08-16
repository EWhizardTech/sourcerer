"use client";

/** Obsidian-style force graph of the library, scoped per subtree.
 * Folders are hubs; files colored by extension; wikilink edges dashed.
 * Click a folder to re-center the graph on it; click a file to open it. */

import { useQuery } from "@tanstack/react-query";
import { ArrowUp, Loader2 } from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { getGraph } from "@/lib/portal-api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

const EXT_COLORS: Record<string, string> = {
  pdf: "#f87171",
  md: "#a78bfa",
  txt: "#94a3b8",
  sql: "#fbbf24",
  ppt: "#fb923c",
  pptx: "#fb923c",
  doc: "#60a5fa",
  docx: "#60a5fa",
  png: "#34d399",
  jpg: "#34d399",
  jpeg: "#34d399",
  mp4: "#22d3ee",
};

interface GraphNodeObject {
  id: string;
  name: string;
  is_folder: boolean;
  ext: string;
  depth: number;
  x?: number;
  y?: number;
}

export default function ResourceGraph() {
  const router = useRouter();
  const [rootId, setRootId] = useState("root");
  const [rootStack, setRootStack] = useState<string[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        setDims({
          width: containerRef.current.clientWidth,
          height: Math.max(480, window.innerHeight - 260),
        });
      }
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ["catalog-graph", rootId],
    queryFn: () => getGraph(rootId, 2, true),
    staleTime: 5 * 60_000,
  });

  const handleClick = useCallback(
    (node: GraphNodeObject) => {
      if (node.is_folder) {
        if (node.id !== rootId) {
          setRootStack((stack) => [...stack, rootId]);
          setRootId(node.id);
        }
      } else {
        // The viewer route handles missing access with a request prompt.
        router.push(`/resources/view/${node.id}`);
      }
    },
    [rootId, router]
  );

  const paintNode = useCallback(
    (node: GraphNodeObject, ctx: CanvasRenderingContext2D, scale: number) => {
      const radius = node.is_folder ? (node.depth === 0 ? 9 : 6) : 3.5;
      ctx.beginPath();
      ctx.arc(node.x!, node.y!, radius, 0, 2 * Math.PI);
      ctx.fillStyle = node.is_folder
        ? node.depth === 0
          ? "#22d3ee"
          : "#8b5cf6"
        : EXT_COLORS[node.ext] ?? "#64748b";
      ctx.fill();
      if (scale > 1.2 || node.is_folder) {
        ctx.font = `${node.is_folder ? 4.5 : 3.5}px sans-serif`;
        ctx.textAlign = "center";
        ctx.fillStyle = "rgba(236,235,245,0.75)";
        ctx.fillText(node.name, node.x!, node.y! + radius + 5);
      }
    },
    []
  );

  return (
    <div ref={containerRef} className="glass relative overflow-hidden">
      <div className="absolute left-3 top-3 z-10 flex items-center gap-2">
        {rootStack.length > 0 && (
          <button
            onClick={() => {
              setRootId(rootStack[rootStack.length - 1]);
              setRootStack((stack) => stack.slice(0, -1));
            }}
            className="glass flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted hover:text-white"
          >
            <ArrowUp className="size-3.5" /> Up a level
          </button>
        )}
        {data?.truncated && (
          <span className="glass px-3 py-1.5 text-xs text-warning">
            Large subtree — showing a sample; zoom in via folders
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="grid h-[480px] place-items-center text-muted">
          <Loader2 className="size-6 animate-spin" />
        </div>
      ) : (
        data && (
          <ForceGraph2D
            width={dims.width}
            height={dims.height}
            graphData={{
              nodes: data.nodes.map((n) => ({ ...n })),
              links: data.links.map((l) => ({ ...l })),
            }}
            backgroundColor="rgba(0,0,0,0)"
            nodeCanvasObject={paintNode as never}
            nodePointerAreaPaint={((node: GraphNodeObject, color: string, ctx: CanvasRenderingContext2D) => {
              ctx.beginPath();
              ctx.arc(node.x!, node.y!, 8, 0, 2 * Math.PI);
              ctx.fillStyle = color;
              ctx.fill();
            }) as never}
            linkColor={((link: { kind: string }) =>
              link.kind === "wiki"
                ? "rgba(167,139,250,0.5)"
                : "rgba(255,255,255,0.12)") as never}
            linkLineDash={((link: { kind: string }) =>
              link.kind === "wiki" ? [2, 2] : null) as never}
            linkWidth={1}
            onNodeClick={handleClick as never}
            cooldownTicks={120}
          />
        )
      )}
    </div>
  );
}
