"""
Chip schema validation (lightweight).

This validator intentionally stays dependency-light while enforcing enough
structure to keep runtime behavior predictable.
"""

from typing import Any, Dict, List


REQUIRED_CHIP_FIELDS = [
    "id",
    "name",
    "version",
    "description",
    "human_benefit",
    "harm_avoidance",
    "risk_level",
]

ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
ALLOWED_ACTIVATION = {"auto", "opt_in"}
OUTCOME_BUCKETS = ("positive", "negative", "neutral")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def validate_chip_spec(spec: Dict[str, Any]) -> List[str]:
    """Validate chip spec. Returns list of errors (empty if valid)."""
    errors: List[str] = []
    if not isinstance(spec, dict):
        return ["spec must be a dict"]

    chip = spec.get("chip")
    if not isinstance(chip, dict):
        return ["spec.chip must be a dict"]

    for field in REQUIRED_CHIP_FIELDS:
        if field not in chip or chip.get(field) in (None, ""):
            errors.append(f"missing chip.{field}")

    risk = chip.get("risk_level")
    if risk and risk not in ALLOWED_RISK_LEVELS:
        errors.append(f"invalid chip.risk_level: {risk}")

    harm_avoidance = chip.get("harm_avoidance")
    if harm_avoidance is not None and not _is_string_list(harm_avoidance):
        errors.append("chip.harm_avoidance must be a list of strings")

    safety_tests = chip.get("safety_tests")
    if safety_tests is not None and not _is_string_list(safety_tests):
        errors.append("chip.safety_tests must be a list of strings if provided")

    activation = chip.get("activation")
    if activation and activation not in ALLOWED_ACTIVATION:
        errors.append(f"invalid chip.activation: {activation}")

    triggers = spec.get("triggers")
    if triggers is not None and not isinstance(triggers, (dict, list)):
        errors.append("triggers must be a dict or list")
    if isinstance(triggers, dict):
        patterns = triggers.get("patterns")
        events = triggers.get("events")
        tools = triggers.get("tools")
        if patterns is not None and not _is_string_list(patterns):
            errors.append("triggers.patterns must be a list of strings")
        if events is not None and not _is_string_list(events):
            errors.append("triggers.events must be a list of strings")
        if tools is not None and not isinstance(tools, list):
            errors.append("triggers.tools must be a list")
        if isinstance(tools, list):
            for idx, tool in enumerate(tools):
                if isinstance(tool, str):
                    continue
                if not isinstance(tool, dict):
                    errors.append(f"triggers.tools[{idx}] must be a dict or string")
                    continue
                if not _is_non_empty_string(tool.get("name", "")):
                    errors.append(f"triggers.tools[{idx}].name is required")
                context_contains = tool.get("context_contains")
                if context_contains is not None and not _is_string_list(context_contains):
                    errors.append(f"triggers.tools[{idx}].context_contains must be a list of strings")

    observers = spec.get("observers")
    if observers is not None and not isinstance(observers, list):
        errors.append("observers must be a list")
    if isinstance(observers, list):
        for oidx, observer in enumerate(observers):
            prefix = f"observers[{oidx}]"
            if not isinstance(observer, dict):
                errors.append(f"{prefix} must be a dict")
                continue
            if not _is_non_empty_string(observer.get("name", "")):
                errors.append(f"{prefix}.name is required")
            if "insight_template" in observer and not isinstance(observer.get("insight_template"), str):
                errors.append(f"{prefix}.insight_template must be a string")
            obs_triggers = observer.get("triggers")
            if obs_triggers is not None and not _is_string_list(obs_triggers):
                errors.append(f"{prefix}.triggers must be a list of strings")

            capture = observer.get("capture")
            if capture is not None and not isinstance(capture, dict):
                errors.append(f"{prefix}.capture must be a dict")
                capture = {}
            if isinstance(capture, dict):
                required = capture.get("required")
                optional = capture.get("optional")
                if required is not None and not isinstance(required, dict):
                    errors.append(f"{prefix}.capture.required must be a dict")
                if optional is not None and not isinstance(optional, dict):
                    errors.append(f"{prefix}.capture.optional must be a dict")

            extraction = observer.get("extraction")
            if extraction is not None and not isinstance(extraction, list):
                errors.append(f"{prefix}.extraction must be a list")
            if isinstance(extraction, list):
                for eidx, ext in enumerate(extraction):
                    e_prefix = f"{prefix}.extraction[{eidx}]"
                    if not isinstance(ext, dict):
                        errors.append(f"{e_prefix} must be a dict")
                        continue
                    if not _is_non_empty_string(ext.get("field", "")):
                        errors.append(f"{e_prefix}.field is required")
                    patterns = ext.get("patterns")
                    keywords = ext.get("keywords")
                    if patterns is None and keywords is None:
                        errors.append(f"{e_prefix} must define patterns or keywords")
                    if patterns is not None and not _is_string_list(patterns):
                        errors.append(f"{e_prefix}.patterns must be a list of strings")
                    if keywords is not None:
                        if not isinstance(keywords, dict):
                            errors.append(f"{e_prefix}.keywords must be a dict")
                        else:
                            for key, value in keywords.items():
                                if not isinstance(key, str):
                                    errors.append(f"{e_prefix}.keywords keys must be strings")
                                if not _is_string_list(value):
                                    errors.append(f"{e_prefix}.keywords[{key}] must be a list of strings")

    outcomes = spec.get("outcomes")
    if outcomes is not None and not isinstance(outcomes, dict):
        errors.append("outcomes must be a dict")
    if isinstance(outcomes, dict):
        for bucket in OUTCOME_BUCKETS:
            entries = outcomes.get(bucket)
            if entries is None:
                continue
            if not isinstance(entries, list):
                errors.append(f"outcomes.{bucket} must be a list")
                continue
            for eidx, entry in enumerate(entries):
                entry_prefix = f"outcomes.{bucket}[{eidx}]"
                if not isinstance(entry, dict):
                    errors.append(f"{entry_prefix} must be a dict")
                    continue
                if not _is_non_empty_string(entry.get("condition", "")):
                    errors.append(f"{entry_prefix}.condition is required")
                if "weight" in entry and not isinstance(entry.get("weight"), (int, float)):
                    errors.append(f"{entry_prefix}.weight must be numeric")
                if "insight" in entry and not isinstance(entry.get("insight"), str):
                    errors.append(f"{entry_prefix}.insight must be a string")
                if "action" in entry and not isinstance(entry.get("action"), str):
                    errors.append(f"{entry_prefix}.action must be a string")

    questions = spec.get("questions")
    if questions is not None and not isinstance(questions, list):
        errors.append("questions must be a list")
    if isinstance(questions, list):
        seen_ids = set()
        for qidx, question in enumerate(questions):
            prefix = f"questions[{qidx}]"
            if not isinstance(question, dict):
                errors.append(f"{prefix} must be a dict")
                continue
            q_id = question.get("id")
            if not _is_non_empty_string(q_id):
                errors.append(f"{prefix}.id is required")
            elif q_id in seen_ids:
                errors.append(f"{prefix}.id is duplicated: {q_id}")
            else:
                seen_ids.add(q_id)
            if not _is_non_empty_string(question.get("question", "")):
                errors.append(f"{prefix}.question is required")

    return errors


def is_valid_chip_spec(spec: Dict[str, Any]) -> bool:
    """Return True if spec passes validation."""
    return len(validate_chip_spec(spec)) == 0
