# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow
[SemVer](https://semver.org/). Promotion flow: `dev → staging → main`
(see `CONTRIBUTING.md`).

## [Unreleased]

## [0.1.0] - 2026-08-16

First tagged release: the Resource Portal beta — Sourcerer as the gated front
door to a Google Drive library.

### Added
- **Resource portal** (`services/portal`): Google OAuth sign-in, metadata-only
  Drive catalog (~5.5k nodes), timed access requests, admin approval/revoke,
  and in-app content viewing (PDF canvas, markdown, text, image, video, and
  office/Google-native → PDF conversion). No content ingestion.
- **Gateway** route for the portal; empty-upstream disables a route
  (portal-only beta).
- **Frontend**: landing / sign-in / sign-up, participant vs admin UIs,
  Drive-style Library + Accessible browsers (grid / list / graph), share links,
  per-viewer watermarking, and copy/print deterrence.
- **Beta deployment** (`deploy/`): Caddy single-origin auto-HTTPS + portal +
  Postgres, with an Azure-for-Students runbook.
- **Content protection**: in-app-only request guard (Sec-Fetch + client header)
  and short-lived, user+file-bound signed content tickets.
- **Session security**: server-side revocation via `session_version`, 24h TTL,
  admin session kill-switch.
- **CI** (`.github/workflows/ci.yml`): portal tests + frontend type-check/build.

### Security
- `nosniff` + sandboxed CSP on content responses (blocks inline HTML/SVG XSS).
- OAuth `email_verified` enforcement; fail-closed production config (session
  secret, root folder, admin list); non-root containers.

### Notes
- Upgrading past this release invalidates existing portal sessions once
  (server-side session versioning was introduced).

[Unreleased]: https://github.com/EWhizardTech/sourcerer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/EWhizardTech/sourcerer/releases/tag/v0.1.0
