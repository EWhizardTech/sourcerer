<!-- Target the right branch: feature/* -> dev, dev -> staging, staging -> main. -->

## What & why

<!-- One or two sentences. Link any issue. -->

## Type

- [ ] Feature
- [ ] Fix
- [ ] Hotfix (branched off `main`; remember to back-merge)
- [ ] Chore / docs / infra

## Checklist

- [ ] Targets the correct branch per the flow (see CONTRIBUTING.md).
- [ ] Portal tests pass locally (`cd services/portal && uv run python -m pytest tests`).
- [ ] Frontend type-checks and builds (`cd frontend && npx tsc --noEmit && npm run build`).
- [ ] No secrets, keys, or real credentials added (checked `git diff`).
- [ ] `CHANGELOG.md` updated if user-facing.
- [ ] Config changes are reflected in the relevant `.env.*.example` / `ENVIRONMENTS.md`.

## Verification

<!-- How you tested. Screenshots for UI. -->
