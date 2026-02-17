#!/usr/bin/env python3
"""A/B benchmark for memory retrieval strategies.

Compares retrieval systems on the same query set:
- embeddings_only
- hybrid
- hybrid_agentic

Inputs:
- JSON file with a top-level "cases" list (or a raw list)

Each case supports:
{
  "id": "short_name",
  "query": "how to rotate auth token safely",
  "relevant_insight_keys": ["insight-123", "insight-456"],
  "relevant_contains": ["rotate token", "credential refresh"]
}

At least one of "relevant_insight_keys" or "relevant_contains" should be
provided for strict quality scoring.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from lib.cognitive_learner import get_cognitive_learner
from lib.embeddings import embed_text
from lib.error_taxonomy import classify_error_kind
from lib.semantic_retriever import SemanticRetriever


SUPPORTED_SYSTEMS = ("embeddings_only", "hybrid", "hybrid_agentic")
INTENT_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "so",
    "that",
    "the",
    "then",
    "to",
    "we",
    "with",
}
LOW_SIGNAL_STRUGGLE_PATTERNS = (
    re.compile(r"\bi struggle with\s+(?:tool[_\s-]*)?\d+[_\s-]*error\s+tasks\b", re.I),
    re.compile(r"\bi struggle with\s+[a-z0-9_]+_error\s+tasks\b", re.I),
    re.compile(r"\bi struggle with\s+[a-z0-9_]+\s+fails with other(?:\s+\(recovered\))?\s+tasks\b", re.I),
)
TRANSCRIPT_ARTIFACT_PATTERNS = (
    re.compile(r"^\s*said it like this[:\s]", re.I),
    re.compile(r"^\s*another reply is[:\s]", re.I),
    re.compile(r"^\s*user wanted[:\s]", re.I),
    re.compile(r"^\s*#\s*spark\s", re.I),
)
METADATA_TELEMETRY_HINTS = (
    "event_type",
    "tool_name",
    "file_path",
    "status:",
    "user_prompt_signal",
    "source: spark_advisory",
)
DEFAULT_RETRIEVAL_KNOBS = {
    "candidate_k": 20,
    "lexical_weight": 0.35,
    "intent_coverage_weight": 0.0,
    "support_boost_weight": 0.0,
    "reliability_weight": 0.0,
    "emotion_state_weight": 0.0,
    "semantic_intent_min": 0.0,
}
_RUNTIME_ADVISOR = None


@dataclass
class EvalCase:
    case_id: str
    query: str
    relevant_insight_keys: List[str] = field(default_factory=list)
    relevant_contains: List[str] = field(default_factory=list)
    notes: str = ""
    emotion_state: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_labels(self) -> bool:
        return bool(self.relevant_insight_keys or self.relevant_contains)


@dataclass
class RetrievedItem:
    insight_key: str
    text: str
    source: str
    semantic_score: float
    fusion_score: float
    score: float
    why: str


@dataclass
class CaseMetrics:
    precision_at_k: Optional[float]
    recall_at_k: Optional[float]
    mrr: Optional[float]
    top1_hit: Optional[bool]
    hits: int
    label_count: int


def percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    idx = (len(ordered) - 1) * max(0.0, min(100.0, p)) / 100.0
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return float(ordered[lo])
    frac = idx - lo
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * frac)


def lexical_overlap_score(query: str, text: str) -> float:
    q = {t for t in re.findall(r"[a-z0-9_]+", query.lower()) if len(t) >= 3}
    d = {t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) >= 3}
    if not q or not d:
        return 0.0
    return len(q & d) / max(1, len(q | d))


def bm25_normalized_scores(query: str, docs: Sequence[str], k1: float = 1.2, b: float = 0.75) -> List[float]:
    if not docs:
        return []
    query_tokens = [t for t in re.findall(r"[a-z0-9_]+", query.lower()) if len(t) >= 3]
    if not query_tokens:
        return [0.0 for _ in docs]

    tokenized_docs = [[t for t in re.findall(r"[a-z0-9_]+", str(doc).lower()) if len(t) >= 3] for doc in docs]
    n_docs = len(tokenized_docs)
    avgdl = sum(len(toks) for toks in tokenized_docs) / max(n_docs, 1)
    if avgdl <= 0:
        return [0.0 for _ in docs]

    df: Dict[str, int] = {}
    for toks in tokenized_docs:
        for tok in set(toks):
            df[tok] = df.get(tok, 0) + 1

    qtf: Dict[str, int] = {}
    for tok in query_tokens:
        qtf[tok] = qtf.get(tok, 0) + 1

    raw: List[float] = []
    for toks in tokenized_docs:
        dl = max(len(toks), 1)
        tf: Dict[str, int] = {}
        for tok in toks:
            tf[tok] = tf.get(tok, 0) + 1

        score = 0.0
        for tok, q_count in qtf.items():
            term_df = df.get(tok, 0)
            if term_df <= 0:
                continue
            idf = math.log(1.0 + ((n_docs - term_df + 0.5) / (term_df + 0.5)))
            term_tf = tf.get(tok, 0)
            if term_tf <= 0:
                continue
            denom = term_tf + k1 * (1.0 - b + (b * (dl / avgdl)))
            if denom <= 0:
                continue
            bm25_term = idf * ((term_tf * (k1 + 1.0)) / denom)
            score += bm25_term * float(q_count)
        raw.append(score)

    mx = max(raw) if raw else 0.0
    if mx <= 0:
        return [0.0 for _ in docs]
    return [float(v / mx) for v in raw]


def hybrid_lexical_scores(
    query: str,
    docs: Sequence[str],
    bm25_mix: float = 0.75,
    k1: float = 1.2,
    b: float = 0.75,
) -> List[float]:
    if not docs:
        return []
    bm25 = bm25_normalized_scores(query=query, docs=docs, k1=k1, b=b)
    overlap = [lexical_overlap_score(query, doc) for doc in docs]
    blend = max(0.0, min(1.0, float(bm25_mix)))
    return [(blend * bm) + ((1.0 - blend) * ov) for bm, ov in zip(bm25, overlap)]


def intent_terms(text: str) -> set:
    tokens = {t for t in re.findall(r"[a-z0-9_]+", str(text or "").lower()) if len(t) >= 3}
    return {t for t in tokens if t not in INTENT_STOPWORDS and not t.isdigit()}


def intent_coverage_score(query_terms: set, text: str) -> float:
    if not query_terms:
        return 0.0
    doc_terms = intent_terms(text)
    if not doc_terms:
        return 0.0
    return len(query_terms & doc_terms) / max(1, len(query_terms))


def is_low_signal_struggle_text(text: str) -> bool:
    sample = str(text or "").strip().lower()
    if not sample:
        return False
    normalized = re.sub(r"^\[[^\]]+\]\s*", "", sample)
    if any(rx.search(normalized) for rx in LOW_SIGNAL_STRUGGLE_PATTERNS):
        return True
    if "i struggle with" not in normalized:
        return False
    noisy_tokens = (
        "_error",
        "mcp__",
        "command_not_found",
        "permission_denied",
        "file_not_found",
        "syntax_error",
        "fails with other",
    )
    return any(tok in normalized for tok in noisy_tokens)


def is_transcript_artifact(text: str) -> bool:
    sample = str(text or "").strip()
    if not sample:
        return False
    lowered = sample.lower()
    if any(rx.match(sample) for rx in TRANSCRIPT_ARTIFACT_PATTERNS):
        return True
    if lowered.startswith("from lib.") and " import " in lowered:
        return True
    return False


def is_metadata_pattern(text: str) -> bool:
    text_stripped = str(text or "").strip()
    if not text_stripped:
        return False
    if re.match(r"^[A-Za-z\s]+:\s*[a-z_]+\s*=\s*.+$", text_stripped):
        return True
    if re.match(r"^(Principle|Style|Setting|Config|Meta|Mode|Level|Type):\s*", text_stripped, re.I):
        action_verbs = [
            "use",
            "avoid",
            "check",
            "verify",
            "ensure",
            "always",
            "never",
            "remember",
            "prefer",
            "try",
            "run",
        ]
        lowered = text_stripped.lower()
        if not any(v in lowered for v in action_verbs):
            return True
    if re.match(r"^[a-z_]+\s*[:=]\s*.+$", text_stripped):
        return True
    if len(text_stripped) < 15 and ":" in text_stripped:
        return True
    incomplete_endings = (
        " that",
        " the",
        " a",
        " an",
        " of",
        " to",
        " for",
        " with",
        " and",
        " or",
        " but",
        " in",
        " on",
        " we",
    )
    return any(text_stripped.lower().endswith(e) for e in incomplete_endings)


def should_drop_candidate_text(text: str, strict_filter: bool) -> bool:
    if not strict_filter:
        return False
    body = str(text or "").strip()
    if not body:
        return True
    lowered = body.lower()
    if is_low_signal_struggle_text(lowered):
        return True
    if is_transcript_artifact(body):
        return True
    if is_metadata_pattern(body):
        return True
    return any(marker in lowered for marker in METADATA_TELEMETRY_HINTS)


def extract_agentic_queries(context: str, limit: int = 3) -> List[str]:
    tokens = []
    skip = {
        "with",
        "from",
        "that",
        "this",
        "into",
        "have",
        "should",
        "would",
        "could",
        "where",
        "when",
        "while",
    }
    for raw in context.lower().replace("/", " ").replace("_", " ").split():
        token = raw.strip(".,:;()[]{}'\"`")
        if len(token) < 4 or token in skip:
            continue
        if not any(ch.isalnum() for ch in token):
            continue
        tokens.append(token)

    unique: List[str] = []
    seen = set()
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        unique.append(token)
        if len(unique) >= limit:
            break

    return [f"{token} failure pattern and fix" for token in unique]


def load_cases(path: Path) -> List[EvalCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    data = raw.get("cases", []) if isinstance(raw, dict) else raw
    if not isinstance(data, list):
        raise ValueError("cases file must contain a list or an object with a 'cases' list")

    cases: List[EvalCase] = []
    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("id") or row.get("case_id") or f"case_{idx + 1}")
        query = str(row.get("query") or "").strip()
        if not query:
            continue
        keys = [str(v).strip() for v in (row.get("relevant_insight_keys") or []) if str(v).strip()]
        contains = [str(v).strip().lower() for v in (row.get("relevant_contains") or []) if str(v).strip()]
        notes = str(row.get("notes") or "")
        emotion_state = row.get("emotion_state") if isinstance(row.get("emotion_state"), dict) else {}
        cases.append(
            EvalCase(
                case_id=case_id,
                query=query,
                relevant_insight_keys=keys,
                relevant_contains=contains,
                notes=notes,
                emotion_state=emotion_state,
            )
        )
    return cases


def _get_runtime_advisor():
    global _RUNTIME_ADVISOR
    if _RUNTIME_ADVISOR is None:
        from lib.advisor import SparkAdvisor

        _RUNTIME_ADVISOR = SparkAdvisor()
    return _RUNTIME_ADVISOR


def runtime_policy_overrides_for_case(
    case: EvalCase,
    *,
    tool_name: str = "Bash",
) -> Dict[str, Any]:
    """Resolve runtime retrieval knobs for a benchmark case from advisor policy."""
    try:
        advisor = _get_runtime_advisor()
        policy = advisor._effective_retrieval_policy(tool_name=tool_name, context=case.query)
        semantic_limit = max(4, int(policy.get("semantic_limit", 8) or 8))
        return {
            "candidate_k": max(20, semantic_limit * 4),
            "lexical_weight": float(policy.get("lexical_weight", DEFAULT_RETRIEVAL_KNOBS["lexical_weight"]) or 0.0),
            "intent_coverage_weight": float(
                policy.get("intent_coverage_weight", DEFAULT_RETRIEVAL_KNOBS["intent_coverage_weight"]) or 0.0
            ),
            "support_boost_weight": float(
                policy.get("support_boost_weight", DEFAULT_RETRIEVAL_KNOBS["support_boost_weight"]) or 0.0
            ),
            "reliability_weight": float(
                policy.get("reliability_weight", DEFAULT_RETRIEVAL_KNOBS["reliability_weight"]) or 0.0
            ),
            "emotion_state_weight": float(
                policy.get("emotion_state_weight", DEFAULT_RETRIEVAL_KNOBS["emotion_state_weight"]) or 0.0
            ),
            "semantic_intent_min": float(
                policy.get("semantic_intent_min", DEFAULT_RETRIEVAL_KNOBS["semantic_intent_min"]) or 0.0
            ),
            "runtime_active_domain": str(policy.get("active_domain") or "general"),
            "runtime_profile_domain": str(policy.get("profile_domain") or "default"),
        }
    except Exception:
        return {}


def resolve_case_knobs(
    *,
    case: EvalCase,
    use_runtime_policy: bool,
    tool_name: str,
    candidate_k: Optional[int],
    lexical_weight: Optional[float],
    intent_coverage_weight: Optional[float],
    support_boost_weight: Optional[float],
    reliability_weight: Optional[float],
    emotion_state_weight: Optional[float] = None,
    semantic_intent_min: Optional[float] = None,
) -> Dict[str, Any]:
    knobs = dict(DEFAULT_RETRIEVAL_KNOBS)
    if use_runtime_policy:
        runtime = runtime_policy_overrides_for_case(case=case, tool_name=tool_name)
        knobs.update({k: v for k, v in runtime.items() if k in knobs})
        if "runtime_active_domain" in runtime:
            knobs["runtime_active_domain"] = runtime["runtime_active_domain"]
        if "runtime_profile_domain" in runtime:
            knobs["runtime_profile_domain"] = runtime["runtime_profile_domain"]

    if candidate_k is not None:
        knobs["candidate_k"] = max(1, int(candidate_k))
    if lexical_weight is not None:
        knobs["lexical_weight"] = float(lexical_weight)
    if intent_coverage_weight is not None:
        knobs["intent_coverage_weight"] = float(intent_coverage_weight)
    if support_boost_weight is not None:
        knobs["support_boost_weight"] = float(support_boost_weight)
    if reliability_weight is not None:
        knobs["reliability_weight"] = float(reliability_weight)
    if emotion_state_weight is not None:
        knobs["emotion_state_weight"] = float(emotion_state_weight)
    if semantic_intent_min is not None:
        knobs["semantic_intent_min"] = float(semantic_intent_min)

    knobs["candidate_k"] = max(1, int(knobs.get("candidate_k", DEFAULT_RETRIEVAL_KNOBS["candidate_k"])))
    knobs["lexical_weight"] = float(knobs.get("lexical_weight", DEFAULT_RETRIEVAL_KNOBS["lexical_weight"]))
    knobs["intent_coverage_weight"] = float(
        knobs.get("intent_coverage_weight", DEFAULT_RETRIEVAL_KNOBS["intent_coverage_weight"])
    )
    knobs["support_boost_weight"] = float(
        knobs.get("support_boost_weight", DEFAULT_RETRIEVAL_KNOBS["support_boost_weight"])
    )
    knobs["reliability_weight"] = float(knobs.get("reliability_weight", DEFAULT_RETRIEVAL_KNOBS["reliability_weight"]))
    knobs["emotion_state_weight"] = float(
        knobs.get("emotion_state_weight", DEFAULT_RETRIEVAL_KNOBS["emotion_state_weight"])
    )
    knobs["semantic_intent_min"] = float(
        knobs.get("semantic_intent_min", DEFAULT_RETRIEVAL_KNOBS["semantic_intent_min"])
    )
    return knobs


def is_item_hit(case: EvalCase, item: RetrievedItem) -> bool:
    key_hit = bool(case.relevant_insight_keys) and item.insight_key in set(case.relevant_insight_keys)
    if key_hit:
        return True
    text = item.text.lower()
    return any(fragment in text for fragment in case.relevant_contains)


def compute_case_metrics(case: EvalCase, items: List[RetrievedItem], k: int) -> CaseMetrics:
    if not case.has_labels:
        return CaseMetrics(
            precision_at_k=None,
            recall_at_k=None,
            mrr=None,
            top1_hit=None,
            hits=0,
            label_count=0,
        )

    top = items[: max(1, k)]
    hits = 0
    first_hit_rank: Optional[int] = None
    for idx, item in enumerate(top, start=1):
        if is_item_hit(case, item):
            hits += 1
            if first_hit_rank is None:
                first_hit_rank = idx

    precision = hits / max(1, len(top))
    label_count = len(case.relevant_insight_keys) if case.relevant_insight_keys else len(case.relevant_contains)
    recall = hits / max(1, label_count)
    mrr = 1.0 / first_hit_rank if first_hit_rank else 0.0
    top1_hit = bool(top and is_item_hit(case, top[0]))

    return CaseMetrics(
        precision_at_k=precision,
        recall_at_k=recall,
        mrr=mrr,
        top1_hit=top1_hit,
        hits=hits,
        label_count=label_count,
    )


def get_insight_text(insight: Any) -> str:
    return str(getattr(insight, "insight", "") or "").strip()


def _extract_insight_emotion_state(insight: Any) -> Dict[str, Any]:
    if insight is None:
        return {}
    direct = getattr(insight, "emotion_state", None)
    if isinstance(direct, dict):
        return direct
    meta = getattr(insight, "meta", None)
    if isinstance(meta, dict):
        emo = meta.get("emotion")
        if isinstance(emo, dict):
            return emo
    return {}


def _emotion_state_similarity(active_state: Dict[str, Any], stored_state: Dict[str, Any]) -> float:
    if not isinstance(active_state, dict) or not isinstance(stored_state, dict):
        return 0.0
    if not active_state or not stored_state:
        return 0.0

    emotion_match = 1.0 if (
        str(active_state.get("primary_emotion") or "").strip()
        and str(active_state.get("primary_emotion") or "").strip()
        == str(stored_state.get("primary_emotion") or "").strip()
    ) else 0.0
    mode_match = 1.0 if (
        str(active_state.get("mode") or "").strip()
        and str(active_state.get("mode") or "").strip()
        == str(stored_state.get("mode") or "").strip()
    ) else 0.0

    axes = ("strain", "calm", "energy", "confidence", "warmth", "playfulness")
    axis_scores: List[float] = []
    for axis in axes:
        if axis not in active_state or axis not in stored_state:
            continue
        try:
            a = max(0.0, min(1.0, float(active_state.get(axis))))
            b = max(0.0, min(1.0, float(stored_state.get(axis))))
        except Exception:
            continue
        axis_scores.append(max(0.0, 1.0 - abs(a - b)))

    axis_similarity = sum(axis_scores) / len(axis_scores) if axis_scores else 0.0
    return max(0.0, min(1.0, (0.50 * axis_similarity) + (0.35 * emotion_match) + (0.15 * mode_match)))


def retrieve_embeddings_only(
    retriever: SemanticRetriever,
    insights: Dict[str, Any],
    query: str,
    top_k: int,
    candidate_k: int,
    noise_filter: Any,
    strict_filter: bool,
) -> List[RetrievedItem]:
    retriever.index.ensure_index(insights, max_items=max(candidate_k * 50, 300), noise_filter=noise_filter)
    qvec = embed_text(query)
    if not qvec:
        # Fallback to lexical overlap when embeddings are disabled/unavailable.
        scored: List[Tuple[float, str, str]] = []
        for key, insight in insights.items():
            text = get_insight_text(insight)
            if not text:
                continue
            if should_drop_candidate_text(text, strict_filter):
                continue
            if noise_filter and noise_filter(text):
                continue
            score = lexical_overlap_score(query, text)
            if score > 0:
                scored.append((score, key, text))
        scored.sort(key=lambda row: row[0], reverse=True)
        return [
            RetrievedItem(
                insight_key=key,
                text=text,
                source="embeddings_only",
                semantic_score=score,
                fusion_score=score,
                score=score,
                why="lexical_fallback",
            )
            for score, key, text in scored[:top_k]
        ]

    ranked = retriever.index.search(qvec, limit=max(candidate_k, top_k))
    items: List[RetrievedItem] = []
    for key, sim in ranked:
        insight = insights.get(key)
        if insight is None:
            continue
        text = get_insight_text(insight)
        if not text:
            continue
        if should_drop_candidate_text(text, strict_filter):
            continue
        if noise_filter and noise_filter(text):
            continue
        items.append(
            RetrievedItem(
                insight_key=key,
                text=text,
                source="embeddings_only",
                semantic_score=float(sim),
                fusion_score=float(sim),
                score=float(sim),
                why=f"semantic={sim:.3f}",
            )
        )
        if len(items) >= top_k:
            break
    return items


def _merge_best(
    merged: Dict[str, RetrievedItem],
    item: RetrievedItem,
) -> None:
    current = merged.get(item.insight_key)
    if current is None or item.score > current.score:
        merged[item.insight_key] = item


def retrieve_hybrid(
    retriever: SemanticRetriever,
    insights: Dict[str, Any],
    query: str,
    top_k: int,
    candidate_k: int,
    lexical_weight: float,
    intent_coverage_weight: float,
    support_boost_weight: float,
    reliability_weight: float,
    emotion_state_weight: float = 0.0,
    semantic_intent_min: float = 0.0,
    strict_filter: bool = True,
    agentic: bool = False,
    emotion_state: Optional[Dict[str, Any]] = None,
) -> List[RetrievedItem]:
    merged: Dict[str, RetrievedItem] = {}
    support_counts: Dict[str, int] = {}
    seen_query_tags: Dict[str, set] = {}
    queries = [query]
    if agentic:
        queries.extend(extract_agentic_queries(query))

    for q in queries[:4]:
        query_tag = "primary" if q == query else q
        results = retriever.retrieve(q, insights, limit=max(candidate_k, top_k))
        for row in results:
            text = str(row.insight_text or "").strip()
            if not text:
                continue
            if should_drop_candidate_text(text, strict_filter):
                continue
            base = float(getattr(row, "fusion_score", 0.0) or 0.0)
            source = "hybrid_agentic" if agentic else "hybrid"
            insight_key = str(row.insight_key or "")
            item = RetrievedItem(
                insight_key=insight_key,
                text=text,
                source=source,
                semantic_score=float(getattr(row, "semantic_sim", 0.0) or 0.0),
                fusion_score=base,
                score=base,
                why=str(getattr(row, "why", "") or ""),
            )
            if insight_key:
                tags = seen_query_tags.setdefault(insight_key, set())
                if query_tag not in tags:
                    tags.add(query_tag)
                    support_counts[insight_key] = int(support_counts.get(insight_key, 0)) + 1
                prev = merged.get(insight_key)
                if prev is None or item.fusion_score > prev.fusion_score:
                    merged[insight_key] = item

    if not merged:
        return []

    query_terms = intent_terms(query)
    merged_items = list(merged.values())
    lexical_scores = hybrid_lexical_scores(query, [item.text for item in merged_items], bm25_mix=0.75, k1=1.2, b=0.75)
    max_support = max(support_counts.values()) if support_counts else 1
    ranked_candidates: List[RetrievedItem] = []
    for idx, item in enumerate(merged_items):
        lex = lexical_scores[idx] if idx < len(lexical_scores) else 0.0
        coverage = intent_coverage_score(query_terms, item.text)
        support = max(1, int(support_counts.get(item.insight_key, 1)))
        support_norm = (support - 1) / max(1, max_support - 1) if max_support > 1 else 0.0
        insight = insights.get(item.insight_key)
        reliability = float(getattr(insight, "reliability", 0.5) or 0.5)
        emotion_similarity = 0.0
        if emotion_state and emotion_state_weight > 0.0:
            emotion_similarity = _emotion_state_similarity(
                emotion_state,
                _extract_insight_emotion_state(insight),
            )
        if item.semantic_score < semantic_intent_min and coverage < semantic_intent_min and item.fusion_score < 0.9:
            continue
        item.score = (
            float(item.fusion_score)
            + (lexical_weight * lex)
            + (intent_coverage_weight * coverage)
            + (support_boost_weight * support_norm)
            + (reliability_weight * reliability)
            + (emotion_state_weight * emotion_similarity)
        )
        item.why = (
            f"{item.why} [lex={lex:.2f} coverage={coverage:.2f} support={support} rel={reliability:.2f} emotion={emotion_similarity:.2f}]"
        ).strip()
        ranked_candidates.append(item)

    ranked = sorted(ranked_candidates, key=lambda item: item.score, reverse=True)
    return ranked[:top_k]


def run_system_for_case(
    *,
    system: str,
    case: EvalCase,
    retriever: SemanticRetriever,
    insights: Dict[str, Any],
    noise_filter: Any,
    top_k: int,
    candidate_k: int,
    lexical_weight: float,
    intent_coverage_weight: float = 0.0,
    support_boost_weight: float = 0.0,
    reliability_weight: float = 0.0,
    emotion_state_weight: float = 0.0,
    semantic_intent_min: float = 0.0,
    strict_filter: bool = True,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    try:
        if system == "embeddings_only":
            items = retrieve_embeddings_only(
                retriever=retriever,
                insights=insights,
                query=case.query,
                top_k=top_k,
                candidate_k=candidate_k,
                noise_filter=noise_filter,
                strict_filter=strict_filter,
            )
        elif system == "hybrid":
            items = retrieve_hybrid(
                retriever=retriever,
                insights=insights,
                query=case.query,
                top_k=top_k,
                candidate_k=candidate_k,
                lexical_weight=lexical_weight,
                intent_coverage_weight=intent_coverage_weight,
                support_boost_weight=support_boost_weight,
                reliability_weight=reliability_weight,
                emotion_state_weight=emotion_state_weight,
                semantic_intent_min=semantic_intent_min,
                strict_filter=strict_filter,
                agentic=False,
                emotion_state=case.emotion_state,
            )
        elif system == "hybrid_agentic":
            items = retrieve_hybrid(
                retriever=retriever,
                insights=insights,
                query=case.query,
                top_k=top_k,
                candidate_k=candidate_k,
                lexical_weight=lexical_weight,
                intent_coverage_weight=intent_coverage_weight,
                support_boost_weight=support_boost_weight,
                reliability_weight=reliability_weight,
                emotion_state_weight=emotion_state_weight,
                semantic_intent_min=semantic_intent_min,
                strict_filter=strict_filter,
                agentic=True,
                emotion_state=case.emotion_state,
            )
        else:
            raise ValueError(f"unsupported system: {system}")

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        metrics = compute_case_metrics(case, items, top_k)
        return {
            "system": system,
            "case_id": case.case_id,
            "elapsed_ms": elapsed_ms,
            "error": None,
            "error_kind": None,
            "result_count": len(items),
            "metrics": asdict(metrics),
            "results": [asdict(item) for item in items],
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        message = str(exc)
        return {
            "system": system,
            "case_id": case.case_id,
            "elapsed_ms": elapsed_ms,
            "error": message,
            "error_kind": classify_error_kind(message),
            "result_count": 0,
            "metrics": asdict(
                CaseMetrics(
                    precision_at_k=None,
                    recall_at_k=None,
                    mrr=None,
                    top1_hit=None,
                    hits=0,
                    label_count=0,
                )
            ),
            "results": [],
        }


def summarize_system(system: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    elapsed = [float(r["elapsed_ms"]) for r in rows]
    labeled = [r for r in rows if r["metrics"]["label_count"] > 0]
    quality_precision = [float(r["metrics"]["precision_at_k"]) for r in labeled if r["metrics"]["precision_at_k"] is not None]
    quality_recall = [float(r["metrics"]["recall_at_k"]) for r in labeled if r["metrics"]["recall_at_k"] is not None]
    quality_mrr = [float(r["metrics"]["mrr"]) for r in labeled if r["metrics"]["mrr"] is not None]
    top1_hits = [
        1.0 if bool(r["metrics"]["top1_hit"]) else 0.0
        for r in labeled
        if r["metrics"]["top1_hit"] is not None
    ]
    error_rows = [r for r in rows if r["error"]]
    error_kinds: Dict[str, int] = {}
    for row in error_rows:
        kind = row["error_kind"] or "unknown"
        error_kinds[kind] = error_kinds.get(kind, 0) + 1

    return {
        "system": system,
        "cases_total": len(rows),
        "cases_labeled": len(labeled),
        "non_empty_rate": round(
            sum(1 for r in rows if r["result_count"] > 0) / max(1, len(rows)),
            4,
        ),
        "precision_at_k": round(sum(quality_precision) / max(1, len(quality_precision)), 4) if quality_precision else None,
        "recall_at_k": round(sum(quality_recall) / max(1, len(quality_recall)), 4) if quality_recall else None,
        "mrr": round(sum(quality_mrr) / max(1, len(quality_mrr)), 4) if quality_mrr else None,
        "top1_hit_rate": round(sum(top1_hits) / max(1, len(top1_hits)), 4) if top1_hits else None,
        "latency_ms_p50": int(percentile(elapsed, 50)),
        "latency_ms_p95": int(percentile(elapsed, 95)),
        "error_rate": round(len(error_rows) / max(1, len(rows)), 4),
        "errors_total": len(error_rows),
        "error_kinds": error_kinds,
    }


def pick_winner(summaries: List[Dict[str, Any]]) -> str:
    if not summaries:
        return "none"

    quality_vectors = {
        (
            row.get("precision_at_k"),
            row.get("recall_at_k"),
            row.get("mrr"),
            row.get("top1_hit_rate"),
        )
        for row in summaries
    }
    # Avoid false "wins" when all systems have identical quality outcomes.
    if len(quality_vectors) == 1:
        return "tie"

    def _score(row: Dict[str, Any]) -> Tuple[float, float, float, float]:
        # Prioritize quality metrics first, then stability, then latency.
        quality = float(row["mrr"] if row["mrr"] is not None else -1.0)
        precision = float(row["precision_at_k"] if row["precision_at_k"] is not None else -1.0)
        stability = 1.0 - float(row.get("error_rate") or 0.0)
        speed = -float(row.get("latency_ms_p95") or 0.0)
        return (quality, precision, stability, speed)

    ranked = sorted(summaries, key=_score, reverse=True)
    if len(ranked) == 1:
        return ranked[0]["system"]
    if _score(ranked[0]) == _score(ranked[1]):
        return "tie"
    return ranked[0]["system"]


def write_markdown_report(report: Dict[str, Any], path: Path) -> None:
    lines: List[str] = []
    meta = report["meta"]
    lines.append("# Memory Retrieval A/B Report")
    lines.append("")
    lines.append(f"- Timestamp (UTC): {meta['timestamp_utc']}")
    lines.append(f"- Cases file: `{meta['cases_file']}`")
    lines.append(f"- Cases: {meta['case_count']}")
    lines.append(f"- Systems: {', '.join(meta['systems'])}")
    lines.append(f"- Top-K: {meta['top_k']}")
    lines.append(f"- Winner: **{report['winner']}**")
    lines.append("")
    lines.append("| System | P@K | Recall@K | MRR | Top1 Hit | Non-empty | p50 ms | p95 ms | Error Rate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in report["summaries"]:
        p = "-" if row["precision_at_k"] is None else f"{row['precision_at_k']:.3f}"
        r = "-" if row["recall_at_k"] is None else f"{row['recall_at_k']:.3f}"
        m = "-" if row["mrr"] is None else f"{row['mrr']:.3f}"
        t = "-" if row["top1_hit_rate"] is None else f"{row['top1_hit_rate']:.3f}"
        lines.append(
            f"| {row['system']} | {p} | {r} | {m} | {t} | "
            f"{row['non_empty_rate']:.3f} | {row['latency_ms_p50']} | {row['latency_ms_p95']} | "
            f"{row['error_rate']:.3f} |"
        )

    lines.append("")
    lines.append("## Error Kinds")
    for row in report["summaries"]:
        kinds = row.get("error_kinds", {})
        if not kinds:
            lines.append(f"- {row['system']}: none")
            continue
        rendered = ", ".join(f"{k}={v}" for k, v in sorted(kinds.items()))
        lines.append(f"- {row['system']}: {rendered}")

    path.write_text("\n".join(lines), encoding="utf-8")


def parse_systems(raw: str) -> List[str]:
    systems = [item.strip() for item in raw.split(",") if item.strip()]
    bad = [system for system in systems if system not in SUPPORTED_SYSTEMS]
    if bad:
        raise ValueError(f"unsupported systems: {', '.join(bad)}")
    if not systems:
        raise ValueError("at least one system is required")
    return systems


def main() -> int:
    parser = argparse.ArgumentParser(description="A/B benchmark for memory retrieval systems")
    parser.add_argument(
        "--cases",
        default=str(Path("benchmarks") / "data" / "memory_retrieval_eval_seed.json"),
        help="Path to benchmark cases JSON",
    )
    parser.add_argument(
        "--systems",
        default="embeddings_only,hybrid,hybrid_agentic",
        help=f"Comma-separated systems ({', '.join(SUPPORTED_SYSTEMS)})",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Top-K results for scoring")
    parser.add_argument("--candidate-k", type=int, default=None, help="Candidate pool per system")
    parser.add_argument("--lexical-weight", type=float, default=None, help="Lexical rerank weight")
    parser.add_argument("--intent-coverage-weight", type=float, default=None, help="Intent coverage rerank weight")
    parser.add_argument("--support-boost-weight", type=float, default=None, help="Cross-query support rerank weight")
    parser.add_argument("--reliability-weight", type=float, default=None, help="Insight reliability rerank weight")
    parser.add_argument("--emotion-state-weight", type=float, default=None, help="Emotion-state rerank weight")
    parser.add_argument(
        "--semantic-intent-min",
        type=float,
        default=None,
        help="Minimum semantic/intent threshold for non-trigger rows",
    )
    parser.add_argument(
        "--use-runtime-policy",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Mirror live advisor retrieval policy/domain profiles while benchmarking",
    )
    parser.add_argument(
        "--runtime-tool-name",
        default="Bash",
        help="Tool name used when resolving runtime retrieval policy per case",
    )
    parser.add_argument(
        "--disable-strict-filter",
        action="store_true",
        help="Disable low-signal cognitive candidate filtering in benchmark retrieval",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=None,
        help="Override semantic min_similarity gate for benchmark runs",
    )
    parser.add_argument(
        "--min-fusion-score",
        type=float,
        default=None,
        help="Override semantic min_fusion_score gate for benchmark runs",
    )
    parser.add_argument(
        "--no-prune-stale-index",
        action="store_true",
        help="Do not prune stale semantic index entries before running",
    )
    parser.add_argument("--out-dir", default=str(Path("benchmarks") / "out"), help="Output directory")
    parser.add_argument("--out-prefix", default="memory_retrieval_ab", help="Output filename prefix")
    parser.add_argument("--case-limit", type=int, default=0, help="Optional max cases")
    parser.add_argument(
        "--strict-labels",
        action="store_true",
        help="Fail if any case is missing labels",
    )
    parser.add_argument(
        "--print-case-results",
        action="store_true",
        help="Print per-case metrics to stdout",
    )
    args = parser.parse_args()

    systems = parse_systems(args.systems)
    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"[ab] missing cases file: {cases_path}")
        return 2

    cases = load_cases(cases_path)
    if args.case_limit and args.case_limit > 0:
        cases = cases[: args.case_limit]
    if not cases:
        print("[ab] no valid cases found")
        return 2

    unlabeled = [case.case_id for case in cases if not case.has_labels]
    if args.strict_labels and unlabeled:
        print(f"[ab] strict labels enabled, unlabeled cases: {', '.join(unlabeled)}")
        return 2

    learner = get_cognitive_learner()
    insights = dict(getattr(learner, "insights", {}) or {})
    noise_filter = getattr(learner, "is_noise_insight", None)
    retriever = SemanticRetriever()
    retriever.config["triggers_enabled"] = False

    pruned_count = None
    if not args.no_prune_stale_index:
        try:
            pruned_count = retriever.index.prune_stale(set(insights.keys()))
        except Exception:
            pruned_count = None

    if args.min_similarity is not None:
        retriever.config["min_similarity"] = float(args.min_similarity)
    if args.min_fusion_score is not None:
        retriever.config["min_fusion_score"] = float(args.min_fusion_score)

    by_system: Dict[str, List[Dict[str, Any]]] = {system: [] for system in systems}
    case_results: List[Dict[str, Any]] = []

    for case in cases:
        knobs = resolve_case_knobs(
            case=case,
            use_runtime_policy=bool(args.use_runtime_policy),
            tool_name=str(args.runtime_tool_name or "Bash"),
            candidate_k=args.candidate_k,
            lexical_weight=args.lexical_weight,
            intent_coverage_weight=args.intent_coverage_weight,
            support_boost_weight=args.support_boost_weight,
            reliability_weight=args.reliability_weight,
            emotion_state_weight=args.emotion_state_weight,
            semantic_intent_min=args.semantic_intent_min,
        )
        per_case: Dict[str, Any] = {
            "case_id": case.case_id,
            "query": case.query,
            "labeled": case.has_labels,
            "resolved_knobs": {
                "candidate_k": int(knobs["candidate_k"]),
                "lexical_weight": float(knobs["lexical_weight"]),
                "intent_coverage_weight": float(knobs["intent_coverage_weight"]),
                "support_boost_weight": float(knobs["support_boost_weight"]),
                "reliability_weight": float(knobs["reliability_weight"]),
                "emotion_state_weight": float(knobs["emotion_state_weight"]),
                "semantic_intent_min": float(knobs["semantic_intent_min"]),
                "runtime_active_domain": str(knobs.get("runtime_active_domain") or ""),
                "runtime_profile_domain": str(knobs.get("runtime_profile_domain") or ""),
            },
            "runs": {},
        }
        for system in systems:
            row = run_system_for_case(
                system=system,
                case=case,
                retriever=retriever,
                insights=insights,
                noise_filter=noise_filter,
                top_k=max(1, int(args.top_k)),
                candidate_k=int(knobs["candidate_k"]),
                lexical_weight=float(knobs["lexical_weight"]),
                intent_coverage_weight=float(knobs["intent_coverage_weight"]),
                support_boost_weight=float(knobs["support_boost_weight"]),
                reliability_weight=float(knobs["reliability_weight"]),
                emotion_state_weight=float(knobs["emotion_state_weight"]),
                semantic_intent_min=float(knobs["semantic_intent_min"]),
                strict_filter=not bool(args.disable_strict_filter),
            )
            by_system[system].append(row)
            per_case["runs"][system] = row
        case_results.append(per_case)

    summaries = [summarize_system(system, by_system[system]) for system in systems]
    winner = pick_winner(summaries)

    report = {
        "meta": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "cases_file": str(cases_path),
            "systems": systems,
            "top_k": int(args.top_k),
            "use_runtime_policy": bool(args.use_runtime_policy),
            "runtime_tool_name": str(args.runtime_tool_name or "Bash"),
            "candidate_k_cli": args.candidate_k,
            "lexical_weight_cli": args.lexical_weight,
            "intent_coverage_weight_cli": args.intent_coverage_weight,
            "support_boost_weight_cli": args.support_boost_weight,
            "reliability_weight_cli": args.reliability_weight,
            "emotion_state_weight_cli": args.emotion_state_weight,
            "semantic_intent_min_cli": args.semantic_intent_min,
            "strict_filter": not bool(args.disable_strict_filter),
            "min_similarity": retriever.config.get("min_similarity"),
            "min_fusion_score": retriever.config.get("min_fusion_score"),
            "stale_index_pruned": False if args.no_prune_stale_index else True,
            "stale_index_pruned_count": pruned_count,
            "case_count": len(cases),
            "labeled_case_count": sum(1 for case in cases if case.has_labels),
            "insight_count": len(insights),
            "python": sys.version.split()[0],
        },
        "winner": winner,
        "summaries": summaries,
        "cases": case_results,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"{args.out_prefix}_report.json"
    out_md = out_dir / f"{args.out_prefix}_report.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown_report(report, out_md)

    print(f"[ab] wrote {out_json}")
    print(f"[ab] wrote {out_md}")
    print(f"[ab] winner={winner}")

    if args.print_case_results:
        for case_row in case_results:
            case_id = case_row["case_id"]
            print(f"\n[case] {case_id}")
            for system in systems:
                row = case_row["runs"][system]
                metrics = row["metrics"]
                print(
                    f"  - {system}: count={row['result_count']} "
                    f"lat={row['elapsed_ms']}ms "
                    f"p={metrics['precision_at_k']} r={metrics['recall_at_k']} "
                    f"mrr={metrics['mrr']} err={row['error_kind']}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
