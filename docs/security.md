# Security

The portal was audited end-to-end and hardened for the beta. This page
describes the enforceable, server-side controls. (The client-side watermark /
copy-deterrence tier is described under [Portal → Frontend protection](services/portal.md#frontend-protection-layer).)

## Content access — in-app only

A granted file's bytes must reach the browser, so an authorized user can always
obtain their own bytes. What the portal *does* enforce is that the content URL
is **useless outside the app** — you cannot copy the `/raw` URL from DevTools,
open it in a new tab, `curl` it, or share it.

Two layers on `/content/{id}/raw` and `/content/{id}/pdf`:

1. **Request-context guard** — rejects top-level navigations using the
   browser-set `Sec-Fetch-*` headers (which page script cannot forge) and
   requires the SPA's `X-Sourcerer-Client` header. `<video>`/`<img>` elements
   (which can't add custom headers) are allowed only as same-origin/-site
   Sec-Fetch media loads.
2. **Signed content ticket** — `GET /content/{id}/meta` mints a short-lived
   HS256 ticket bound to the file id **and** the viewer's Google `sub`, passed
   as `?t=` on the content URL. `/raw` and `/pdf` reject a missing, expired, or
   mismatched ticket. TTL is 5 minutes for one-shot fetches (PDF/image/text) and
   6 hours for streamed media (a single `<video>` URL must outlast playback).

Result: pasting the raw URL in a new tab → **403**; bare `curl` → **403**;
sharing the link to a non-granted user → **403**; and even a copied in-app URL
expires quickly and is bound to one user.

!!! warning "Accepted limitation"
    A **granted** user who scripts the app's exact `fetch()` (their own cookie
    + header + a freshly-minted ticket) still gets their own bytes — inherent
    to being allowed to view the file, the same class as OS screenshots. The
    only stronger tier is **server-side PDF rasterization** (serve watermarked
    page images, never the source file), which is not implemented.

## Response hardening

Content responses set `X-Content-Type-Options: nosniff` and a sandboxed CSP
(`default-src 'none'; sandbox`) and force `attachment` for active types
(HTML/SVG/XML) — this closes a same-origin XSS where `/raw` would otherwise
serve a Drive-typed HTML/SVG file inline in the app's origin. In prod, Caddy
adds HSTS, `nosniff`, `X-Frame-Options: DENY`, and a Referrer-Policy.

## Sessions

Sessions are stateless HS256 JWTs with **server-side revocation** via
`users.session_version`: the token carries an `sv` claim; `current_user`
rejects any token whose `sv` is stale. **Logout bumps the counter**, so a
captured cookie is dead server-side (not merely cleared client-side).
Admins can force-logout a user with `POST /admin/users/{id}/revoke-sessions`.
Token TTL is 24 hours. Admin status is derived from `ADMIN_EMAILS` per request —
never trusted from the token — and the OAuth callback requires `email_verified`.

## Fail-closed configuration

In production (`PORTAL_COOKIE_SECURE=true`) the service refuses to boot unless
`PORTAL_SESSION_SECRET` is strong (≥32 chars, non-default),
`PORTAL_ROOT_FOLDER_ID` is set, and `ADMIN_EMAILS` is non-empty. The beta
compose additionally `${VAR:?}`-guards `SITE_ADDRESS`, `POSTGRES_PASSWORD`,
`PORTAL_SESSION_SECRET`, and `PORTAL_ROOT_FOLDER_ID`, so an incomplete deploy
fails loudly rather than booting insecure.

## Platform hardening

- Containers run **non-root** (portal/gateway uid 10001, frontend uid 1000).
  The mounted service-account key must be readable by that user (mode 644).
- No secrets are committed (both service-account keys are gitignored and absent
  from history); `secrets/` is mounted read-only.
- CSRF origin guard fails closed on a missing `Origin` for state-changing
  methods (belt-and-braces on top of `SameSite=Lax` + single origin).
- The office→PDF converter uses `create_subprocess_exec` (list argv, no shell);
  no command injection, no path traversal (cache keyed by real Drive ids), and
  no SSRF (Drive host/scheme are hardcoded).

## Access-control invariants

Access is resolved by one indexed materialized-path check
(`:target_path_ids LIKE granted.path_ids || '%'`), with LIKE metacharacters
escaped and paths slash-anchored so sibling prefixes can't leak. Grants are
re-checked live on every content hit (revoke/expiry are immediate), admin routes
are uniformly gated, and no request/grant endpoint exposes another user's data.
Every content view and admin decision is written to `audit_events`.
