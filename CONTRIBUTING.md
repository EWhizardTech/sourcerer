# Contributing & Git flow

Sourcerer uses a three-tier promotion flow. Code always moves **up**:

```
feature/*  ┐
fix/*      ├─▶  dev  ──▶  staging  ──▶  main
hotfix/*   ┘   (integration)  (pre-prod)  (production)
```

| Branch | Purpose | Deploys to | Who writes |
|---|---|---|---|
| `main` | Production. Always releasable. Tagged. | prod VM | PR from `staging` only |
| `staging` | Pre-prod validation, mirrors prod config. | staging VM | PR from `dev` only |
| `dev` | Integration of finished features. | dev / local | PR from `feature/*` |
| `feature/*`, `fix/*` | One change in progress. | — | you |
| `hotfix/*` | Urgent prod fix (see below). | — | you |

## Day-to-day

1. Branch off **`dev`**: `git switch dev && git pull && git switch -c feature/my-thing`.
2. Commit small, run tests locally (below), open a PR into **`dev`**.
3. CI (`.github/workflows/ci.yml`) must pass: portal `pytest`, frontend `tsc` + `build`.
4. Merge to `dev`. When a set of features is ready, open **`dev → staging`**, deploy staging, smoke-test.
5. When staging is green, open **`staging → main`**, tag a release, deploy prod.

Never push directly to `main` or `staging` — always via PR. `dev` may take direct pushes for small integration fixes, but a PR is preferred.

## Hotfix

For an urgent production bug:

1. Branch `hotfix/xyz` off **`main`**.
2. PR into `main`, tag a patch release, deploy.
3. **Back-merge** `main` into `staging` and `dev` so the fix isn't lost:
   `git switch staging && git merge main` (then the same into `dev`).

## Running tests locally

```bash
# Portal (Python)
cd services/portal && uv run python -m pytest tests -q

# Frontend
cd frontend && npm ci && npx tsc --noEmit && npm run build
```

## Release checklist (staging → main)

- [ ] `staging` deploy is green and smoke-tested (sign-in, request, approve, view).
- [ ] `CHANGELOG.md` updated under a new version heading.
- [ ] PR `staging → main` opened; CI green.
- [ ] Merge, then tag: `git switch main && git pull && git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z`.
- [ ] Deploy prod (`deploy/` runbook), verify `/health`.
- [ ] Back-merge `main → staging → dev` if the release added commits on `main`.

## Commit messages

Imperative subject, wrap the body, explain the *why*. This project does **not** add
AI co-author trailers to commits.

## Environments & config

See [`deploy/ENVIRONMENTS.md`](deploy/ENVIRONMENTS.md) for the per-tier config
(origins, cookie flags, secrets) and which compose file each tier uses.
