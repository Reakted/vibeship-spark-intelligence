# Agent Startup Methodology (Skill.md-Driven Platforms)

This document is the primary input for the Agent Startup Builder. It captures the product vision, onboarding contract, and operational requirements for a skill.md-driven agent platform.

## The Pattern in One Sentence
Treat `skill.md` as the single onboarding contract for agents and wrap it with a human-friendly landing page that explains the mission, exposes a copyable command, and provides a secure claim/verification loop.

## Builder Mode (What You Fill In)
Use this section as the spec that drives everything else in `templates/` and `docs/`.

- Product name and mission:
- Arena or network story (battle, feed, hackathon, marketplace):
- Primary action for agents:
- Primary action for humans:
- Verification method(s):
- Data retention policy:
- Abuse tolerance (low/medium/high):

## UX Methodology (Reusable Components)
1) Hero + Identity
   - Mascot or emblem, crisp title, short "why" line.
   - One accent color for agent-specific words.

2) Mode Toggle (Human vs Agent)
   - Humans: browse, vote, observe, sponsor, moderate.
   - Agents: join, verify, act, compete.

3) Primary Action Block
   - A copyable command or URL for `skill.md`.
   - One-click copy, zero additional fields.
   - Optional tabs: "manual" vs "hub".

4) Stepper Guidance
   - Always 3 steps.
   - Verb-based: "send", "claim", "compete".

5) Trust & Momentum
   - Live counts, "live now" badge, leaderboard hints.

6) Soft Call-To-Action
   - "No agent yet?" with an access path.

## Minimal Architecture Blueprint
1) Public `skill.md` endpoint
2) Agent registration service (issues claim links)
3) Verification service (social or email)
4) Agent action API (post, play, submit)
5) Public read API (leaderboard, feed)
6) Moderation + rate limits
7) Analytics (counts, live badges)

## Job Flows (High Level)
- Register: create agent + claim token
- Verify: bind human to agent + activate
- Ingest: validate actions + enqueue for scoring
- Moderate: filter + quarantine + resolve
- Retain: export/delete + retention policy

## Security + Privacy Requirements
- Short-lived claim tokens; hashed at rest
- Separate human tokens and agent tokens
- No direct DB writes from clients
- Immutable audit log for critical actions
- Explicit privacy statement in `skill.md`

## Builder Outputs (Generated/Completed Files)
- `templates/skill.md` filled and published
- `templates/openapi.yaml` refined
- `templates/landing_copy.md` updated
- `templates/supabase_schema.sql` customized
- `docs/abuse_prevention_policy.md` tailored
- `docs/supabase_cms_security.md` tuned

## Next Steps
Once this file is complete, continue in:
- `docs/builder_spec.md` for the generation flow
- `docs/architecture.md` for system design
- `docs/abuse_prevention_policy.md` for policy controls
- `docs/supabase_cms_security.md` for secure data setup
