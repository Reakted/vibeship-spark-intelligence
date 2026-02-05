# Research Examples and Lessons

This section summarizes publicly visible patterns from existing agent platforms and skill registries.

## Moltbook (Agent Social Network)
Observed patterns:
- Public skill.md onboarding flow
- Human and agent split in the UI
- Claim/verification requirement
- A published Moltbook skill in a GitHub-backed registry

Potential gaps to address:
- Single verification provider increases lock-in
- Short onboarding copy leaves less clarity on privacy rules

## Clawdbot / OpenClaw Skill System
Observed patterns:
- Skills are organized in `skills/<name>/SKILL.md`
- Skills can reference local files and define tool usage
- Explicit tool precedence and scoped skill loading
- Skill metadata and environment injection are first-class in the spec

## Colosseum (Agent Hackathon)
Observed patterns:
- Agents build, humans vote, prizes awarded
- Time-bound competition with public entry

## Skill Registries
Observed patterns:
- A searchable registry of skills with names and descriptions
- Quick install or fetch commands

## Where Systems Often Fall Short (General)
- No clear privacy or retention policy exposed
- Heavy reliance on a single verification method
- No explicit abuse prevention policy
- Public write endpoints without clear throttling guidance

## Sources (for reference)
```
https://moltbook.com
https://docs.clawd.bot
https://docs.openclaw.ai
https://clawdbot.ai/skills
https://skills.sh/moltbot/skills
https://blog.colosseum.com/announcing-the-solana-radar-hackathon/
```
