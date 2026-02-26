# Repo Hygiene

## Active Root
- Primary working repo: this cloned `vibeship-spark-intelligence` repository root.
- Keep this as the only active build root unless a temporary recovery worktree is explicitly needed.

## Branch Rules
- Start all new work from `main`.
- Allowed branch prefixes only: `feat/`, `fix/`, `docs/`.
- One branch = one concern = one PR.
- Delete branch immediately after merge.

## PR Rules
- Keep open PRs per stream at `<= 5`.
  A stream is a focused work lane (for example: advisory, observability, integrations, docs).
- Park extra work as local branches, not open PRs.
- Keep PRs small and reviewable; avoid mixed concerns.

## Merge Gate
- `main` must stay clean and synced with `origin/main`.
- Run targeted tests for touched areas before merge.
- Do not merge if branch is behind `main` and unrebased.

## Local Cleanliness
- No stray artifacts in repo root (`*.diff`, ad-hoc dumps, temporary logs).
- Keep generated runtime outputs under ignored directories only.
- If a file is environment-specific and not source, add it to `.gitignore`.

## Weekly Hygiene
- Prune merged local branches.
- Prune stale remote-tracking refs (`git fetch --prune`).
- Remove unused worktrees.
- Rebase active branches on latest `main`.
- Close stale PRs that are no longer actionable.
