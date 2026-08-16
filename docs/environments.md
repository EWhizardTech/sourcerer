# Environments & Git flow

## Branch flow

Code is promoted **upward**; each long-lived branch maps to a deploy tier.

```
feature/*  ┐
fix/*      ├─▶  dev  ──▶  staging  ──▶  main
hotfix/*   ┘   (integration)  (pre-prod)  (production)
```

- Branch features off `dev`; open a PR into `dev`.
- Promote `dev → staging` (deploy + smoke-test), then `staging → main` (tag +
  deploy prod). Never push directly to `main`/`staging`.
- Hotfixes branch off `main`, then back-merge into `staging` and `dev`.

CI (`.github/workflows/ci.yml`) runs the portal test suite and the frontend
type-check/build on every PR and push to these branches. Full rules,
hotfix procedure, and the release checklist are in `CONTRIBUTING.md` at the
repo root.

## Deploy tiers

| Tier | Branch | Compose file | Env source | Cookies | Origin |
|---|---|---|---|---|---|
| **dev** | `dev` | `docker-compose.yml` (root) | `.env` from `.env.schema` | insecure, `Lax` | `localhost:3000/3001` |
| **staging** | `staging` | `deploy/docker-compose.beta.yml` | `deploy/.env` from `.env.staging.example` | `Secure`, `Lax` | `https://<staging host>` |
| **prod** | `main` | `deploy/docker-compose.beta.yml` | `deploy/.env` from `.env.beta.example` | `Secure`, `Lax` | `https://<prod host>` |

Staging and prod run the **same** single-origin stack (Caddy auto-HTTPS →
frontend + gateway → portal → postgres); they differ only by their
`deploy/.env`. Keep their secrets, DB passwords, `SITE_ADDRESS`, and ideally
their OAuth clients **distinct**. See `deploy/ENVIRONMENTS.md` and
[Deployment](deployment.md) for the runbook, backups, and TLS.
