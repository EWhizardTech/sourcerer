# HANDOFF — Sourcerer Resource Portal

Context document for engineers/agents picking up this repo. Covers what the
portal is, how it's built, the security model, the git flow, deployment, and
the accepted limitations. Current release: **v0.1.0** (portal beta).

---

## 1. What this project is

**Sourcerer** started as a RAG platform (chat/quiz/ingestion over a Google
Drive corpus). The **Resource Portal** (`services/portal`) is the current,
shipped feature and the whole of the **beta**: it makes Sourcerer the *only
front door* to the owner's Google Drive folder `Academic_Resources`
(~22k files, ~22 GB, Semesters 01–09 + an Obsidian vault; Drive folder ID
`1f8E8ZIZO0Rhfwi6VO3OJlGBIMLDDaemL`).

Users sign in with Google, see a **metadata-only index**, request **timed
access** to folders/files, an **admin approves/adjusts/revokes**, and granted
users view content **in-app only**. Drive URLs are never exposed; bytes stream
through a read-only service account.

### HARD constraint — no ingestion, no cloud cost
The portal performs **zero** content ingestion: no embeddings, no Qdrant
writes, no Groq/Gemini/LLM calls, no Celery. Catalog sync stores Drive
**metadata only** (ids/names/sizes/paths). File bytes move on demand for one
granted file at a time. The only external API is the free Google Drive API.
RAG/LLM over this content is explicitly *future* work. **Do not add ingestion
to the portal path.**

The RAG services (`ingestion`, `retrieval`, `quiz`) still exist in the repo but
are **disabled in the beta deployment** (gateway upstreams empty → their routes
404).

---

## 2. Branches & git flow

Promotion flows **up**: `feature/* → dev → staging → main`. All three
long-lived branches currently point at the same release commit (`v0.1.0`).

- `main` — production, tagged, releasable. PRs from `staging` only.
- `staging` — pre-prod, mirrors prod config. PRs from `dev` only.
- `dev` — integration; branch features from here.

Full rules, hotfix procedure, and the release checklist are in
[`CONTRIBUTING.md`](CONTRIBUTING.md). CI (`.github/workflows/ci.yml`) runs
portal `pytest` + frontend `tsc`/`build` on PRs/pushes to these branches.

> **Branch protection is NOT yet enforced** — it needs a repo **admin** (the
> automation account has only push/triage). Apply the rules from CONTRIBUTING
> for `main` + `staging` (require PR + the `backend`/`frontend` checks).

---

## 3. Architecture

uv workspace monorepo, Python 3.13, FastAPI. Everything is fronted by the
**gateway** (`/api/v1/*` reverse proxy, streaming, aggregate `/health`).

```
Browser ─▶ Caddy (prod) / gateway:8001 (dev) ─▶ portal:8000 ─▶ Postgres
                                              └▶ (RAG services, disabled in beta)
```

| Service | Port (dev) | Role |
|---|---|---|
| frontend | 3000 (docker) / 3001 (`next dev`) | Next.js 15 App Router UI |
| gateway | 8001→8000 | httpx streaming reverse proxy |
| portal | 8000 (internal) | auth, catalog, grants, content |
| postgres | 5433→5432 | portal's relational store |
| ingestion/retrieval/quiz | — | RAG; disabled in beta |

Prod/staging use `deploy/docker-compose.beta.yml`: **Caddy single-origin
auto-HTTPS → frontend + gateway → portal → postgres**. Same-origin means
first-party `SameSite=Lax; Secure` cookies and no CORS.

---

## 4. Portal internals

### Auth (portal-native OAuth, no Auth.js)
`services/portal/app/routes/auth.py` runs the Google OAuth code flow itself
(confidential client) and issues an HS256 JWT cookie `sourcerer_session`
(`app/services/security.py`). Claims: `sub, email, name, sv, exp`. Admin =
email in `ADMIN_EMAILS`, derived **server-side per request** (`app/deps.py`),
never trusted from the token. The ID token is validated (`iss`/`aud`/`exp`/
`email_verified`) — bytes come straight from Google's token endpoint over TLS.

### Catalog (metadata only)
`app/services/{gdrive,catalog_sync}.py` walk `PORTAL_ROOT_FOLDER_ID` into
`drive_nodes` (BFS, one `files.list` per folder — Drive silently returns empty
for 3+ OR'd `'x' in parents`). Mark-and-sweep on `synced_at`. Materialized path
`path_ids` = `/rootId/aId/selfId/`. Excludes dot-dirs + `PORTAL_SYNC_EXCLUDE`.
Obsidian `[[wikilinks]]` → `md_links` (graph view).

### Access model
Request (`access_requests` + items) → admin approve → one `grants` row per
item. **Folder grant covers its whole subtree** via one indexed
`:target_path_ids LIKE granted.path_ids || '%'` check
(`app/services/access.py`), with `_` / `%` / `\` LIKE-escaped and slash-anchored
paths so siblings can't leak. `grants.node_id` has **no FK** (survives sweeps;
a grant on a vanished node matches nothing). Access is re-checked live on every
content hit — revoke/expiry take effect immediately.

### Content
`app/routes/content.py`: `/meta` (viewer routing + mints a content ticket),
`/raw` (Range-aware Drive streaming; `Accept-Encoding: identity` because Drive
gzips), `/pdf` (LibreOffice for office, Drive export for Google-native;
content-addressed disk cache keyed by md5/modifiedTime, per-file lock +
`Semaphore(2)`). Every successful view writes an `audit_events` row before
streaming.

---

## 5. Security model (read before touching auth/content)

The portal was audited end-to-end (6-dimension review) and hardened. Layers:

### Content access — in-app only + signed tickets
Bytes are gated so the raw URL is useless outside the app
(`_guard_content_request` + signed ticket in `content.py`):
1. **Request-context guard** — rejects top-level navigations via `Sec-Fetch-*`
   (browser-set, unforgeable) and requires the SPA header `X-Sourcerer-Client`.
   `<video>`/`<img>` (which can't add headers) are allowed only as
   same-origin/-site Sec-Fetch media loads.
2. **Signed ticket** — `/meta` mints an HS256 ticket bound to `file_id` +
   viewer `sub`, `?t=` on the content URL. TTL: 5 min for one-shot fetches,
   6 h for streamed media (a single `<video>` URL must outlast playback).
   `/raw` and `/pdf` reject missing/expired/mismatched tickets.

Net: pasting the `/raw` URL in a new tab → **403**; bare `curl` → **403**;
sharing the link to a non-granted user → **403**.

> **Irreducible limitation (accepted):** a *granted* user who scripts the app's
> exact `fetch()` (own cookie + header + a freshly-minted ticket) still gets
> their own bytes. That's inherent to being allowed to view the file — same
> class as screenshots (the deterrence tier already accepts OS screenshots).
> The only tier beyond this is **server-side PDF rasterization** (send
> watermarked page images, never the source file) — not implemented.

### Response hardening
Content responses set `X-Content-Type-Options: nosniff` and a sandboxed CSP
(`default-src 'none'; sandbox`) and force `attachment` for active types
(HTML/SVG/XML) — closes a same-origin XSS where `/raw` served Drive-typed HTML
inline. Caddy adds HSTS, nosniff, `X-Frame-Options: DENY`, Referrer-Policy.

### Sessions
Server-side revocation via `users.session_version` (migration `0002`): the JWT
carries `sv`; `current_user` rejects stale tokens; **logout bumps the counter**
(a captured cookie dies server-side, not just client-side); admin kill-switch
`POST /admin/users/{id}/revoke-sessions`. TTL 24 h.

### Fail-closed config
`libs/sourcerer-core/sourcerer_core/config.py` refuses to boot in production
(`PORTAL_COOKIE_SECURE=true`) unless `PORTAL_SESSION_SECRET` is strong/non-default
(≥32 chars), `PORTAL_ROOT_FOLDER_ID` is set, and `ADMIN_EMAILS` is non-empty.
`deploy/docker-compose.beta.yml` `${VAR:?}`-guards `SITE_ADDRESS`,
`POSTGRES_PASSWORD`, `PORTAL_SESSION_SECRET`, `PORTAL_ROOT_FOLDER_ID`.

### Other
Containers run **non-root** (portal/gateway uid 10001, frontend uid 1000 —
portal note: the mounted SA key must be mode 644). No committed secrets (both
service-account keys are gitignored, absent from history). CSRF origin guard
fails closed on missing Origin. LibreOffice subprocess uses `create_subprocess_exec`
(list argv, no shell). No SSRF (host/scheme hardcoded).

### Frontend deterrence tier (not DRM)
`components/portal/protected-content.tsx`: tiled email watermark (baked into PDF
canvas bitmaps too), context-menu/selection/drag suppression, clipboard
truncation, print blanking, blur-on-tab-blur, DevTools heuristic. Explicitly
deterrence — OS screenshots can't be blocked.

---

## 6. Deployment

Per-tier config in [`deploy/ENVIRONMENTS.md`](deploy/ENVIRONMENTS.md):
- **dev** → root `docker-compose.yml`, `.env` from `.env.schema`, cookies insecure.
- **staging** → `deploy/docker-compose.beta.yml`, `.env` from `.env.staging.example`.
- **prod** → same beta compose, `.env` from `.env.beta.example`.

Runbook (Azure-for-Students, TLS, backups): `deploy/README.md`. Migrations run
automatically (`alembic upgrade head` in the portal CMD). Healthchecks +
`service_healthy` gating so Caddy doesn't proxy before upstreams are ready.

### VM-side to-dos (can't be done from the repo)
- `chmod 644 secrets/acc.json` (portal runs non-root).
- Keep only the SA key you use in `secrets/` (whole dir is mounted ro).
- Schedule the `pg_dump` backup — users/grants/audit live only in `pgdata`.

---

## 7. Testing

```bash
cd services/portal && uv run python -m pytest tests -q   # 30 tests
cd frontend && npm ci && npx tsc --noEmit && npm run build
```

Test files (`services/portal/tests/`): `test_access.py` (grant semantics),
`test_sync.py` (upsert/move/sweep, wikilinks), `test_security.py` (JWT + admin
+ content tickets), `test_sessions.py` (revocation), `test_content_guard.py`
(Sec-Fetch/header guard). Tests build the schema from ORM metadata on
`sqlite+aiosqlite` (NOT from Alembic — keep migration `0001`/`0002` in sync with
`models.py` by hand; a migration test is a known TODO).

---

## 8. Key files

| Area | Path |
|---|---|
| Auth / session | `services/portal/app/routes/auth.py`, `app/services/security.py`, `app/deps.py` |
| Access resolution | `services/portal/app/services/access.py` |
| Content proxy + guards | `services/portal/app/routes/content.py` |
| Converter (LibreOffice) | `services/portal/app/services/converter.py` |
| Catalog sync | `services/portal/app/services/{gdrive,catalog_sync}.py` |
| Admin API | `services/portal/app/routes/admin.py` |
| Models / migrations | `services/portal/app/db/models.py`, `alembic/versions/000{1,2}_*.py` |
| Shared config (fail-closed) | `libs/sourcerer-core/sourcerer_core/config.py` |
| Gateway proxy | `services/gateway/app/main.py` |
| Frontend API client | `frontend/lib/portal-api.ts` |
| Viewers / protection | `frontend/components/portal/{viewers,protected-content,share-menu,file-browser}.tsx` |
| Beta deploy | `deploy/docker-compose.beta.yml`, `deploy/Caddyfile`, `deploy/README.md` |

---

## 9. Gotchas (empirically discovered — don't relearn the hard way)

- Drive silently returns **empty** for 3+ OR'd `'x' in parents` — one
  `files.list` per folder.
- Drive `alt=media` responses are **gzipped**; forward `Accept-Encoding:
  identity` or PDFs corrupt ("Invalid PDF structure").
- `cannotDownloadFile` 403 = the folder's "viewers can't download" flag; fixed
  by giving the SA **Editor** (safe — OAuth scope is `drive.readonly`).
- Gateway must rebuild response headers from `multi_items()` — a dict collapses
  duplicate `Set-Cookie` (was the sign-in loop).
- pdf.js worker must be served from `/public` (`workerSrc =
  "/pdf.worker.min.mjs"`) — the `new URL()` trick breaks under the Next dev
  bundler ("`__webpack_require__.U is not a constructor`").
- `<video crossOrigin="use-credentials">` stalls in Chrome — omit it.
- `npm run build` in `frontend/` clobbers a running `next dev` `.next`; the
  host dev server runs on **3001** (`next dev -p 3001`), docker frontend on 3000.
- After changing portal code you must **rebuild AND recreate** the container
  (`docker compose build portal && docker compose up -d portal`) — a running
  container keeps old code (this bit us: a guard looked bypassed because the
  container was stale).

---

## 10. Open follow-ups

- **Branch protection** — needs a repo admin (see §2).
- **Admin Users UI** — the session kill-switch has an API + client method
  (`adminRevokeSessions`) but no button; there's no Users panel yet.
- **Server-side PDF rasterization** — the next content-protection tier (§5), if
  content sensitivity justifies the cost.
- **RAG re-enable** — the gateway has **no auth** and the RAG services don't
  self-gate; add auth before ever setting their upstream URLs.
- **Migration test** — run `alembic upgrade head` against a throwaway DB in CI
  to catch model↔migration drift.
- Bump GitHub Action versions (Node 20 deprecation warning in CI).

See `CHANGELOG.md` for the released feature list.
