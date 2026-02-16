# Advisory Preferences: 2-Question Setup + Anytime Updates (Shipped)

Date: 2026-02-16  
Status: live in `main`

## What was added

Spark now has a user-facing advisory preference layer that can be set in 1-2 questions and changed later without code edits.

### 1) Preference model + persistence

File: `lib/advisory_preferences.py`

- New user-facing knobs:
  - `memory_mode`: `off | standard | replay`
  - `guidance_style`: `concise | balanced | coach`
- Stores values in `~/.spark/tuneables.json` under:
  - `advisor.*` (runtime controls)
  - `advisory_preferences.*` (metadata/audit trail)
- Applies derived runtime thresholds from the two choices:
  - replay sensitivity (`replay_*`)
  - advice amount/strictness (`max_items`, `min_rank_score`)
- Hot applies via `lib.advisor.reload_advisor_config()` (best effort; no restart needed for supported values).

### 2) Runtime reload support in advisor

File: `lib/advisor.py`

- Added reloadable advisory preference fields:
  - `replay_mode`, `guidance_style`
  - `replay_enabled`, `replay_min_strict`, `replay_min_delta`
  - `replay_max_records`, `replay_max_age_s`, `replay_strict_window_s`, `replay_min_context`
- Added `reload_advisor_config()` to expose active effective values after reload.

### 3) Dashboard API endpoints

File: `dashboard.py`

- `GET /api/advisory/setup`
  - Returns current preferences and the 2-question setup schema/options.
- `GET /api/advisory/preferences`
  - Returns current effective preference state.
- `POST /api/advisory/setup`
  - Applies selected values.
- `POST /api/advisory/preferences`
  - Applies selected values.

Payload shape for `POST`:

```json
{
  "memory_mode": "standard",
  "guidance_style": "balanced",
  "source": "dashboard"
}
```

### 4) CLI setup (2 prompts)

File: `scripts/advisory_setup.py`

- Interactive run:
  - `python scripts/advisory_setup.py`
- Non-interactive run:
  - `python scripts/advisory_setup.py --memory-mode replay --guidance-style coach`
- Show current:
  - `python scripts/advisory_setup.py --show`

## Why this design

- Two questions are enough for most users:
  - "How much history replay should Spark use?"
  - "How deep/verbose should guidance be?"
- Internally, Spark maps those to stable low-level tuneables automatically.
- Users can change anytime through API or CLI with immediate runtime effect.

## Verification

Targeted tests passing:

- `tests/test_advisory_preferences.py`
- `tests/test_dashboard_advisory_status.py`
- `tests/test_advisor_replay.py`
- `tests/test_advisor_config_loader.py`

Run:

```bash
python -m pytest -q tests/test_advisory_preferences.py tests/test_dashboard_advisory_status.py tests/test_advisor_replay.py tests/test_advisor_config_loader.py
```

Result: `14 passed` (with a non-blocking Windows temp-dir permission warning at pytest exit).

## User-facing behavior summary

- First-time setup can be done in 1-2 answers.
- Defaults are guided (`standard`, `balanced`).
- Values persist in tuneables and survive restarts.
- Settings can be changed later via:
  - dashboard API
  - CLI helper
  - direct tuneables edit (advanced users)
