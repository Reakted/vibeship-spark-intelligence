# Report: CLI Run Summary — Learning Loop Visibility
Date: 2026-02-11
Owner: Spark

## Context
Need lower confusion during rapid iteration by surfacing key learning-loop signals directly in run summary output.

## Findings
1. Completion and recurrence signals existed in JSON output but were not visible in default CLI run summary.
2. Operators benefit from seeing learning-loop state in the same console pane as generation/scoring/follow-up.

## Evidence
- spark-forge commit `ce88336`
- Updated `src/spark_forge/cli.py` summary section

## Decisions
- Keep: print completion status, live validation source, recurrence risk, unsupported decision count in run summary.
- Roll back: none.
- Iterate: later colorize/threshold highlight if needed.

## Next actions
1. Continue one-by-one implementation commits.
2. Validate clarity gains in next live run sequence.

## Confidence
high
