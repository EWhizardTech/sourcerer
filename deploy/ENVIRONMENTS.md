# Environments

Three tiers, mapped to the three long-lived branches (see `../CONTRIBUTING.md`).

| Tier | Branch | Compose file | Env source | Cookies | Origin |
|---|---|---|---|---|---|
| **dev** | `dev` | `docker-compose.yml` (root) | root `.env` (from `.env.schema`) | `Secure=false`, `SameSite=Lax` | `http://localhost:3000/3001` |
| **staging** | `staging` | `deploy/docker-compose.beta.yml` | `deploy/.env` (from `.env.staging.example`) | `Secure=true`, `SameSite=Lax` | `https://<staging host>` |
| **prod** | `main` | `deploy/docker-compose.beta.yml` | `deploy/.env` (from `.env.beta.example`) | `Secure=true`, `SameSite=Lax` | `https://<prod host>` |

Staging and prod run the **same** stack (Caddy single-origin, auto-HTTPS); they
differ only by `deploy/.env`. Keep their secrets, DB passwords, `SITE_ADDRESS`,
and ideally their OAuth clients **distinct**.

## Fail-closed guards (don't fight them)

In staging/prod (`PORTAL_COOKIE_SECURE=true`) the app refuses to boot unless:

- `PORTAL_SESSION_SECRET` is a strong, non-default value (≥ 32 chars),
- `PORTAL_ROOT_FOLDER_ID` is set,
- `ADMIN_EMAILS` lists at least one admin.

And `docker compose` itself hard-fails if `SITE_ADDRESS`, `POSTGRES_PASSWORD`,
`PORTAL_SESSION_SECRET`, or `PORTAL_ROOT_FOLDER_ID` are missing from `deploy/.env`.

## Bring up a tier

```bash
# dev (local)
cp .env.schema .env      # fill in, then:
docker compose up -d --build

# staging / prod (on the VM, in deploy/)
cp .env.staging.example .env   # or .env.beta.example for prod; fill in
docker compose -f docker-compose.beta.yml up -d --build
```

Operational notes (backups, key permissions, TLS) live in `README.md`.
