#!/usr/bin/env python3
"""ID Connector - Link traces to Spark's ID systems.

Connects tracer events to:
- EIDOS episodes/steps via trace_id
- Advisory packets via advisory_id
- Agent feedback via trace_id
- Cognitive insights via session_id/timestamp
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any


SPARK_DIR = Path.home() / ".spark"
EIDOS_DB_PATH = SPARK_DIR / "eidos.db"


@dataclass
class EidosStepLink:
    """Link to an EIDOS step."""
    step_id: str
    episode_id: str
    episode_goal: str
    intent: str
    prediction: str
    result: str
    evaluation: str
    lesson: str
    confidence_before: float
    confidence_after: float
    surprise_level: float
    created_at: float


@dataclass
class EidosEpisodeLink:
    """Link to an EIDOS episode."""
    episode_id: str
    goal: str
    outcome: str
    phase: str
    step_count: int
    final_evaluation: str
    start_ts: float
    end_ts: Optional[float]
    steps: List[EidosStepLink] = field(default_factory=list)


@dataclass
class AdvisoryLink:
    """Link to an advisory packet."""
    advisory_id: str
    task_plane: str
    intent_family: str
    route: str
    advice: str
    emitted: bool
    timestamp: float


@dataclass
class AgentFeedbackLink:
    """Link to an agent feedback report."""
    report_id: str
    task: str
    action_taken: str
    outcome: str
    success: bool
    lesson_learned: Optional[str]
    confidence: float
    timestamp: float


@dataclass
class CognitiveInsightLink:
    """Link to a cognitive insight."""
    insight_id: str
    category: str
    signal: str
    confidence: float
    times_validated: int
    timestamp: float


@dataclass
class TraceContext:
    """Full context for a trace from all ID systems."""
    trace_id: str
    session_id: str
    eidos_episodes: List[EidosEpisodeLink] = field(default_factory=list)
    advisories: List[AdvisoryLink] = field(default_factory=list)
    agent_feedback: List[AgentFeedbackLink] = field(default_factory=list)
    cognitive_insights: List[CognitiveInsightLink] = field(default_factory=list)


class IDConnector:
    """Connects traces to Spark's various ID systems."""
    
    def __init__(self, spark_dir: Optional[Path] = None):
        self.spark_dir = spark_dir or SPARK_DIR
        self.eidos_path = self.spark_dir / "eidos.db"
        self.advisory_path = self.spark_dir / "advisory_engine.jsonl"
        self.feedback_dir = Path("spark_reports")
        self.cognitive_path = self.spark_dir / "cognitive_insights.json"
    
    # ==================== EIDOS Integration ====================
    
    def get_eidos_by_trace_id(self, trace_id: str) -> List[EidosStepLink]:
        """Get EIDOS steps linked to a trace_id."""
        if not self.eidos_path.exists():
            return []
        
        steps = []
        try:
            with sqlite3.connect(str(self.eidos_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """SELECT s.*, e.goal as episode_goal 
                       FROM steps s
                       JOIN episodes e ON s.episode_id = e.episode_id
                       WHERE s.trace_id = ?
                       ORDER BY s.created_at""",
                    (trace_id,)
                ).fetchall()
                
                for row in rows:
                    steps.append(EidosStepLink(
                        step_id=row["step_id"],
                        episode_id=row["episode_id"],
                        episode_goal=row["episode_goal"] or "",
                        intent=row["intent"] or "",
                        prediction=row["prediction"] or "",
                        result=row["result"] or "",
                        evaluation=row["evaluation"] or "unknown",
                        lesson=row["lesson"] or "",
                        confidence_before=row["confidence_before"] or 0.0,
                        confidence_after=row["confidence_after"] or 0.0,
                        surprise_level=row["surprise_level"] or 0.0,
                        created_at=row["created_at"] or 0.0,
                    ))
        except Exception as e:
            print(f"[IDConnector] EIDOS query error: {e}")
        
        return steps
    
    def get_eidos_episode_for_trace(self, trace_id: str) -> Optional[EidosEpisodeLink]:
        """Get full EIDOS episode context for a trace."""
        steps = self.get_eidos_by_trace_id(trace_id)
        if not steps:
            return None
        
        # Get episode details from first step
        episode_id = steps[0].episode_id
        
        try:
            with sqlite3.connect(str(self.eidos_path)) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM episodes WHERE episode_id = ?",
                    (episode_id,)
                ).fetchone()
                
                if row:
                    return EidosEpisodeLink(
                        episode_id=row["episode_id"],
                        goal=row["goal"] or "",
                        outcome=row["outcome"] or "in_progress",
                        phase=row["phase"] or "explore",
                        step_count=row["step_count"] or 0,
                        final_evaluation=row["final_evaluation"] or "",
                        start_ts=row["start_ts"] or 0.0,
                        end_ts=row["end_ts"],
                        steps=steps,
                    )
        except Exception as e:
            print(f"[IDConnector] EIDOS episode query error: {e}")
        
        return None
    
    # ==================== Advisory Integration ====================
    
    def get_advisories_by_trace_id(self, trace_id: str) -> List[AdvisoryLink]:
        """Get advisory packets linked to a trace_id."""
        if not self.advisory_path.exists():
            return []
        
        advisories = []
        try:
            with open(self.advisory_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        if event.get('trace_id') == trace_id:
                            advisories.append(AdvisoryLink(
                                advisory_id=event.get('advisory_id') or event.get('packet_id') or 'unknown',
                                task_plane=event.get('task_plane', 'unknown'),
                                intent_family=event.get('intent_family', ''),
                                route=event.get('route', ''),
                                advice=str(event.get('advice', ''))[:200],
                                emitted=event.get('emitted', False),
                                timestamp=event.get('timestamp', 0.0),
                            ))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[IDConnector] Advisory query error: {e}")
        
        # Return most recent first
        return sorted(advisories, key=lambda a: a.timestamp, reverse=True)
    
    # ==================== Agent Feedback Integration ====================
    
    def get_feedback_by_trace_id(self, trace_id: str) -> List[AgentFeedbackLink]:
        """Get agent feedback reports linked to a trace_id."""
        feedback = []
        
        if not self.feedback_dir.exists():
            return feedback
        
        try:
            for report_file in self.feedback_dir.glob("*.json"):
                try:
                    data = json.loads(report_file.read_text())
                    if data.get('trace_id') == trace_id:
                        feedback.append(AgentFeedbackLink(
                            report_id=data.get('report_id', 'unknown'),
                            task=data.get('task', ''),
                            action_taken=data.get('action_taken', ''),
                            outcome=data.get('outcome', ''),
                            success=data.get('success', False),
                            lesson_learned=data.get('lesson_learned'),
                            confidence=data.get('confidence', 0.0),
                            timestamp=data.get('submitted_at', 0.0),
                        ))
                except Exception:
                    continue
        except Exception as e:
            print(f"[IDConnector] Feedback query error: {e}")
        
        return sorted(feedback, key=lambda f: f.timestamp, reverse=True)
    
    # ==================== Cognitive Insights Integration ====================
    
    def get_insights_by_session(self, session_id: str, since: float = 0.0) -> List[CognitiveInsightLink]:
        """Get cognitive insights for a session since a timestamp."""
        if not self.cognitive_path.exists():
            return []
        
        insights = []
        try:
            data = json.loads(self.cognitive_path.read_text())
            for insight in data.get('insights', []):
                ts = insight.get('timestamp', 0.0)
                if ts >= since:
                    insights.append(CognitiveInsightLink(
                        insight_id=insight.get('id', 'unknown'),
                        category=insight.get('category', 'general'),
                        signal=insight.get('signal', insight.get('text', '')),
                        confidence=insight.get('confidence', 0.0),
                        times_validated=insight.get('times_validated', 0),
                        timestamp=ts,
                    ))
        except Exception as e:
            print(f"[IDConnector] Cognitive insights query error: {e}")
        
        return sorted(insights, key=lambda i: i.timestamp, reverse=True)
    
    # ==================== Full Context Assembly ====================
    
    def get_full_context(self, trace_id: str, session_id: str) -> TraceContext:
        """Get full context for a trace from all ID systems."""
        return TraceContext(
            trace_id=trace_id,
            session_id=session_id,
            eidos_episodes=self._get_eidos_context(trace_id),
            advisories=self.get_advisories_by_trace_id(trace_id),
            agent_feedback=self.get_feedback_by_trace_id(trace_id),
            cognitive_insights=self.get_insights_by_session(session_id, since=time.time() - 3600),
        )
    
    def _get_eidos_context(self, trace_id: str) -> List[EidosEpisodeLink]:
        """Get EIDOS episodes for a trace."""
        episode = self.get_eidos_episode_for_trace(trace_id)
        return [episode] if episode else []
    
    # ==================== Session Correlation ====================
    
    def get_session_timeline(self, session_id: str) -> Dict[str, Any]:
        """Get a timeline of all ID system activity for a session."""
        timeline = {
            'session_id': session_id,
            'eidos_episodes': [],
            'advisories': [],
            'feedback': [],
            'insights': [],
        }
        
        # Get EIDOS episodes that might be related (based on timestamp proximity)
        if self.eidos_path.exists():
            try:
                with sqlite3.connect(str(self.eidos_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute(
                        "SELECT * FROM episodes ORDER BY start_ts DESC LIMIT 20"
                    ).fetchall()
                    for row in rows:
                        timeline['eidos_episodes'].append({
                            'episode_id': row["episode_id"],
                            'goal': row["goal"][:60] if row["goal"] else "",
                            'outcome': row["outcome"],
                            'step_count': row["step_count"],
                        })
            except Exception:
                pass
        
        return timeline


def demo_connector():
    """Demo the ID connector."""
    connector = IDConnector()
    
    # Get some recent trace IDs from EIDOS
    print("=== ID Connector Demo ===")
    print()
    
    # Check EIDOS for recent steps with trace_ids
    if connector.eidos_path.exists():
        with sqlite3.connect(str(connector.eidos_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT trace_id, episode_id, intent FROM steps WHERE trace_id IS NOT NULL ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
            
            print(f"Found {len(rows)} recent EIDOS steps with trace_ids")
            for row in rows:
                trace_id = row["trace_id"]
                print(f"\nTrace: {trace_id[:20]}...")
                print(f"  Intent: {row['intent'][:50]}...")
                
                # Get full context
                context = connector.get_full_context(trace_id, "demo")
                print(f"  EIDOS episodes: {len(context.eidos_episodes)}")
                print(f"  Advisories: {len(context.advisories)}")
                print(f"  Feedback: {len(context.agent_feedback)}")
                
                if context.eidos_episodes:
                    ep = context.eidos_episodes[0]
                    print(f"  Episode goal: {ep.goal[:40]}...")
                    if ep.steps:
                        step = ep.steps[0]
                        print(f"  Prediction: {step.prediction[:40]}..." if step.prediction else "  No prediction")
                        print(f"  Lesson: {step.lesson[:40]}..." if step.lesson else "  No lesson")


if __name__ == "__main__":
    demo_connector()
