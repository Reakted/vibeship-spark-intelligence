# 2026-02-13 — Soul Upgrade integration notes

## What shipped
- Added `lib/soul_upgrade.py` as lightweight integration bridge to Pulse companion consciousness endpoint:
  - `fetch_soul_state(session_id, base_url)`
  - `soul_kernel_pass(state)`
  - `guidance_preface(state)`

## Why
- Keep Soul/Consciousness logic modular while enabling spark-intelligence to consume live mood + kernel state.
- Preserve separation of concerns:
  - `vibeship-spark-consciousness`: evolving modules
  - `vibeship-spark-pulse`: UI + endpoint
  - `vibeship-spark-intelligence`: orchestrator/consumer

## Next
- Wire `guidance_preface(...)` into advisory synthesis path behind a feature flag.
- Track kernel-pass metric in advice emissions.
