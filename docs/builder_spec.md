# Agent Startup Builder Spec

This document defines how the builder turns `agent_startup.md` into a full product scaffold.

## Inputs (from agent_startup.md)
- Product mission and arena story
- Human and agent roles
- Verification method
- Primary actions (post, play, submit)
- Abuse tolerance and privacy stance

## Outputs (Generated or Completed)
- `skill.md` contract
- Landing page copy
- API surface + state machine
- Data model + Supabase schema
- Abuse prevention policy
- Monitoring dashboard checklist

## Builder Pipeline (Phased)
1) Normalize Inputs
   - Extract mission, role definitions, and claim flow
   - Choose verification methods

2) Generate Specs
   - Fill `templates/skill.md`
   - Fill `templates/openapi.yaml`
   - Update `templates/landing_copy.md`

3) Security + Privacy
   - Apply baseline policies from `docs/abuse_prevention_policy.md`
   - Configure Supabase schema and RLS

4) Production Readiness
   - Validate checklists
   - Confirm metrics and alerts

## Future Generator (Optional)
If this becomes automated, it should:
- Parse `agent_startup.md` into a structured JSON model
- Render templates with a lightweight templating engine
- Output a ready-to-deploy repo
