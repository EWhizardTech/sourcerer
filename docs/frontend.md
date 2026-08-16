# Frontend

`frontend/` — a decoupled Next.js (App Router) web app talking to the gateway.

## Pages

| Route | What it does |
|---|---|
| `/` | Dashboard — live health cards for the gateway and each service (15 s polling), quick actions |
| `/chat` | Streaming chat: token-by-token rendering, expandable source citation cards with score bars, session memory, stop/new-chat controls, Markdown answers |
| `/quiz` | Quiz generator + interactive player: one question at a time, instant feedback, difficulty badges, results screen with per-question review |
| `/ingestion` | Drive folder submission with queued-file feedback |

## Stack

- **Next.js** (App Router, standalone output for Docker)
- **Tailwind CSS v4** — design tokens in `app/globals.css` (dark glass theme, violet→cyan gradient accents)
- **framer-motion** — page and card animations
- **react-markdown + remark-gfm** — answer rendering
- **lucide-react** — icons

## API access

All requests go through the gateway, configured at build time:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
```

Streaming uses `fetch` + `ReadableStream` with a small SSE frame parser (`lib/api.ts` → `streamChat`), so answers render token-by-token and source cards appear the moment retrieval completes.

## Development

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev   # http://localhost:3001
```
