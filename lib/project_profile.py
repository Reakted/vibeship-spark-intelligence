"""Project profile and questioning helpers.

Lightweight, local-only storage for project-level goals, decisions, and domain insights.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.diagnostics import log_debug
from lib.memory_banks import infer_project_key
from lib.project_context import get_project_context


PROJECT_DIR = Path.home() / ".spark" / "projects"

DOMAIN_QUESTIONS: Dict[str, List[Dict[str, str]]] = {
    "game_dev": [
        {"id": "game_core_loop", "category": "done", "question": "What makes the core loop satisfying?"},
        {"id": "game_feedback", "category": "quality", "question": "What immediate feedback must the player feel?"},
        {"id": "game_physics", "category": "insight", "question": "Any critical physics balance or tuning rules?"},
        {"id": "game_pacing", "category": "quality", "question": "What pace feels right for this experience?"},
        {"id": "game_definition_done", "category": "done", "question": "How will we know the game feels complete?"},
    ],
    "product": [
        {"id": "product_activation", "category": "metric", "question": "What is the activation metric for this product?"},
        {"id": "product_value", "category": "done", "question": "What does 'done' mean for users?"},
        {"id": "product_onboarding", "category": "quality", "question": "Where do users struggle in onboarding?"},
        {"id": "product_kpi", "category": "metric", "question": "Which KPI matters most right now?"},
        {"id": "product_risk", "category": "risk", "question": "What could make this fail after launch?"},
    ],
    "marketing": [
        {"id": "mkt_audience", "category": "goal", "question": "Who is the primary audience?"},
        {"id": "mkt_kpi", "category": "metric", "question": "What is the primary KPI (CTR, CAC, MQL)?"},
        {"id": "mkt_message", "category": "insight", "question": "What message or hook should resonate most?"},
        {"id": "mkt_channel", "category": "strategy", "question": "Which channel is most important?"},
        {"id": "mkt_done", "category": "done", "question": "What does success look like for this campaign?"},
    ],
    "org": [
        {"id": "org_goal", "category": "goal", "question": "What operational outcome matters most?"},
        {"id": "org_bottleneck", "category": "risk", "question": "Where is the main bottleneck or handoff risk?"},
        {"id": "org_metric", "category": "metric", "question": "Which metric tells us we're improving?"},
        {"id": "org_decision", "category": "decision", "question": "What hard decision are we making now?"},
        {"id": "org_done", "category": "done", "question": "What does 'done' mean operationally?"},
    ],
    "engineering": [
        {"id": "eng_arch", "category": "decision", "question": "What architecture decision matters most?"},
        {"id": "eng_risk", "category": "risk", "question": "What will cause problems later if ignored?"},
        {"id": "eng_done", "category": "done", "question": "What signals completion beyond tests passing?"},
        {"id": "eng_perf", "category": "quality", "question": "What performance or reliability target matters?"},
        {"id": "eng_constraint", "category": "goal", "question": "What constraints must we respect?"},
    ],
    "general": [
        {"id": "gen_goal", "category": "goal", "question": "What is the project goal in one sentence?"},
        {"id": "gen_done", "category": "done", "question": "How will we know it's complete?"},
        {"id": "gen_risk", "category": "risk", "question": "What could make this fail later?"},
        {"id": "gen_quality", "category": "quality", "question": "What quality signal matters most?"},
        {"id": "gen_feedback", "category": "feedback", "question": "Who gives feedback and how often?"},
    ],
}


def _now() -> float:
    return time.time()


def _default_profile(project_key: str, domain: str) -> Dict[str, Any]:
    return {
        "project_key": project_key,
        "domain": domain,
        "created_at": _now(),
        "updated_at": _now(),
        "phase": "discovery",
        "questions": [],
        "answers": [],
        "goals": [],
        "done": "",
        "done_history": [],
        "milestones": [],
        "decisions": [],
        "insights": [],
        "feedback": [],
        "risks": [],
    }


def _profile_path(project_key: str) -> Path:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECT_DIR / f"{project_key}.json"


def infer_domain(project_dir: Optional[Path] = None, hint: Optional[str] = None) -> str:
    if hint:
        return hint

    root = Path(project_dir or Path.cwd()).resolve()
    name = root.name.lower()
    try:
        ctx = get_project_context(root)
    except Exception:
        ctx = {}

    tokens = " ".join([name] + (ctx.get("languages") or []) + (ctx.get("frameworks") or []) + (ctx.get("tools") or []))
    tokens = tokens.lower()

    if any(t in tokens for t in ("unity", "godot", "unreal", "pygame", "phaser", "game")):
        return "game_dev"
    if any(t in tokens for t in ("marketing", "campaign", "seo", "growth")):
        return "marketing"
    if any(t in tokens for t in ("org", "ops", "operations", "process")):
        return "org"
    if any(t in tokens for t in ("product", "saas", "onboarding")):
        return "product"
    if any(t in tokens for t in ("backend", "api", "service", "infra")):
        return "engineering"

    return "general"


def get_project_key(project_dir: Optional[Path] = None) -> str:
    key = infer_project_key()
    if key:
        return key
    root = Path(project_dir or Path.cwd()).resolve()
    return root.name or "default"


def load_profile(project_dir: Optional[Path] = None) -> Dict[str, Any]:
    project_key = get_project_key(project_dir)
    path = _profile_path(project_key)
    if not path.exists():
        domain = infer_domain(project_dir)
        return _default_profile(project_key, domain)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid_profile")
        if not data.get("phase"):
            data["phase"] = "discovery"
            save_profile(data)
        return data
    except Exception as e:
        log_debug("project_profile", "load_profile failed", e)
        domain = infer_domain(project_dir)
        return _default_profile(project_key, domain)


def save_profile(profile: Dict[str, Any]) -> None:
    project_key = profile.get("project_key") or "default"
    profile["updated_at"] = _now()
    path = _profile_path(project_key)
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")


def list_profiles() -> List[Dict[str, Any]]:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    profiles: List[Dict[str, Any]] = []
    for path in PROJECT_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                profiles.append(data)
        except Exception:
            continue
    return profiles


def ensure_questions(profile: Dict[str, Any]) -> int:
    domain = profile.get("domain") or "general"
    pool = DOMAIN_QUESTIONS.get(domain, DOMAIN_QUESTIONS["general"])
    existing = {q.get("id") for q in profile.get("questions", []) if isinstance(q, dict)}
    added = 0
    for q in pool:
        if q["id"] in existing:
            continue
        profile.setdefault("questions", []).append({
            "id": q["id"],
            "category": q["category"],
            "question": q["question"],
            "asked_at": None,
            "answered_at": None,
        })
        added += 1
    if added:
        save_profile(profile)
    return added


def record_answer(profile: Dict[str, Any], question_id: str, answer: str) -> Optional[Dict[str, Any]]:
    if not question_id or not answer:
        return None
    now = _now()
    questions = profile.get("questions") or []
    found = None
    for q in questions:
        if q.get("id") == question_id:
            q["answered_at"] = now
            found = q
            break
    entry = {
        "question_id": question_id,
        "answer": answer.strip(),
        "category": (found.get("category") if found else "general"),
        "answered_at": now,
    }
    profile.setdefault("answers", []).append(entry)
    save_profile(profile)
    return entry


def record_entry(profile: Dict[str, Any], entry_type: str, text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = _now()
    entry = {
        "entry_id": _hash_id(profile.get("project_key") or "", entry_type, (text or "").strip()[:160]),
        "text": (text or "").strip(),
        "created_at": now,
        "meta": meta or {},
    }
    target = entry_type
    if entry_type == "done":
        target = "done_history"
    bucket = profile.setdefault(target, [])
    if isinstance(bucket, list):
        bucket.append(entry)
    else:
        profile[target] = [entry]
    save_profile(profile)
    return entry


def set_phase(profile: Dict[str, Any], phase: str) -> None:
    phase_val = (phase or "").strip().lower()
    if not phase_val:
        return
    profile["phase"] = phase_val
    record_entry(profile, "phase_history", f"phase -> {phase_val}", meta={})
