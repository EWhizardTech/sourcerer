/** Gateway API client + SSE stream reader. */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

/* ---------- Types ---------- */

export interface ServiceHealth {
  status: string;
  [key: string]: unknown;
}

export interface AggregateHealth {
  status: string;
  gateway: string;
  services: Record<string, ServiceHealth>;
}

export interface ChatSource {
  id: number;
  chunk_id: string;
  text: string;
  source: string;
  page_number: number | null;
  score: number | null;
  course_code?: string;
  subject?: string;
  topic?: string;
  url?: string;
  type: "document" | "web";
}

export interface QuizItem {
  question: string;
  answer: string;
  options: string[];
  difficulty: string;
  source_chunk_ids: string[];
}

export interface IngestedFile {
  file_id: string;
  file_name: string;
  mime_type: string;
  file_path: string;
  modified_time: string;
  folder_metadata: Record<string, unknown>;
}

export type ChatStreamEvent =
  | { event: "session"; session_id: string }
  | { event: "sources"; sources: ChatSource[] }
  | { event: "token"; text: string }
  | {
      event: "done";
      answer: string;
      sources: ChatSource[];
      session_id: string;
      condensed_query: string | null;
    }
  | { event: "error"; detail: string };

/* ---------- REST helpers ---------- */

async function jsonOrThrow<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* keep default detail */
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

export async function getHealth(): Promise<AggregateHealth> {
  return jsonOrThrow(await fetch(`${API_URL}/health`, { cache: "no-store" }));
}

export async function generateQuiz(params: {
  query: string;
  course_code?: string;
  year?: string;
  tags?: string[];
  num_questions: number;
}): Promise<QuizItem[]> {
  return jsonOrThrow(
    await fetch(`${API_URL}/api/v1/quiz/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: params.query,
        filters: {
          course_code: params.course_code || null,
          year: params.year || null,
          tags: params.tags?.length ? params.tags : null,
        },
        num_questions: params.num_questions,
      }),
    })
  );
}

export async function ingestGdrive(params: {
  folder_id: string;
  course_code?: string;
  year?: string;
  include_root_as_tag: boolean;
}): Promise<IngestedFile[]> {
  return jsonOrThrow(
    await fetch(`${API_URL}/api/v1/ingest/gdrive`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        folder_id: params.folder_id,
        course_code: params.course_code || null,
        year: params.year || null,
        include_root_as_tag: params.include_root_as_tag,
      }),
    })
  );
}

export async function clearChatSession(sessionId: string): Promise<void> {
  await fetch(`${API_URL}/api/v1/chat/${sessionId}`, { method: "DELETE" });
}

/* ---------- SSE chat stream ---------- */

export async function* streamChat(
  query: string,
  sessionId: string | null,
  signal?: AbortSignal
): AsyncGenerator<ChatStreamEvent> {
  const resp = await fetch(`${API_URL}/api/v1/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId }),
    signal,
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`Stream failed: ${resp.status} ${resp.statusText}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line.
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);

        let eventName = "message";
        const dataLines: string[] = [];
        for (const line of frame.split("\n")) {
          if (line.startsWith("event:")) eventName = line.slice(6).trim();
          else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
        }
        if (!dataLines.length) continue;

        try {
          const data = JSON.parse(dataLines.join("\n"));
          yield { event: eventName, ...data } as ChatStreamEvent;
        } catch {
          /* skip malformed frame */
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
