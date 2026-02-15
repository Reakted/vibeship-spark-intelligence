# Security Policy

## Reporting a Vulnerability

If you believe you found a security vulnerability or a safety-critical issue:
- Do not open a public GitHub issue with exploit details.
- Instead, email a private report to the maintainers.

Before any public launch, set a dedicated security contact email and (optionally) a PGP key:
- Security contact: `security@vibeship.co`
- PGP (optional): add fingerprint + public key here

Include:
- what you found (impact, affected component)
- minimal reproduction steps
- suggested fix if you have one

## Scope

This repo handles:
- local event capture (Claude Code hooks, OpenClaw tailer)
- processing and memory/distillation loops (Spark / EIDOS)
- local dashboards and notifications

Security-sensitive areas:
- hook inputs (prompt injection via tool metadata)
- any code execution surfaces (shell/tool runners)
- any network clients (Mind bridge, notify/wake endpoints)
- any persisted files under `~/.spark/` and `~/.openclaw/`

## Coordinated Disclosure (Suggested Defaults)

- Acknowledge within: 72 hours
- Initial assessment within: 7 days
- Patch target for critical issues: 14 days (best-effort)

## Hard Rules

- Never ask reporters to publish exploit details.
- Never request real secrets from reporters.
