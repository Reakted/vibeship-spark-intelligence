"""
Spark Promoter: Auto-promote high-value insights to project files

When a cognitive insight proves reliable enough (high validation count,
high reliability score), it should be promoted to permanent project 
documentation where it will always be loaded.

Promotion targets:
- CLAUDE.md - Project conventions, gotchas, facts
- AGENTS.md - Workflow patterns, tool usage, delegation rules
- TOOLS.md - Tool-specific insights, integration gotchas
- SOUL.md - Behavioral patterns, communication style (Clawdbot)

Promotion criteria:
- Reliability >= 70%
- Times validated >= 3
- Not already promoted
- Category matches target file
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from .cognitive_learner import CognitiveInsight, CognitiveCategory, get_cognitive_learner


# ============= Configuration =============
DEFAULT_PROMOTION_THRESHOLD = 0.7  # 70% reliability
DEFAULT_MIN_VALIDATIONS = 3


@dataclass
class PromotionTarget:
    """Definition of a promotion target file."""
    filename: str
    section: str
    categories: List[CognitiveCategory]
    description: str


# Promotion target definitions
PROMOTION_TARGETS = [
    PromotionTarget(
        filename="CLAUDE.md",
        section="## Spark Learnings",
        categories=[
            CognitiveCategory.WISDOM,
            CognitiveCategory.REASONING,
            CognitiveCategory.CONTEXT,
        ],
        description="Project conventions, gotchas, and verified patterns"
    ),
    PromotionTarget(
        filename="AGENTS.md",
        section="## Spark Learnings",
        categories=[
            CognitiveCategory.META_LEARNING,
            CognitiveCategory.SELF_AWARENESS,
        ],
        description="Workflow patterns and self-awareness insights"
    ),
    PromotionTarget(
        filename="TOOLS.md",
        section="## Spark Learnings", 
        categories=[
            CognitiveCategory.CONTEXT,
        ],
        description="Tool-specific insights and integration gotchas"
    ),
    PromotionTarget(
        filename="SOUL.md",
        section="## Spark Learnings",
        categories=[
            CognitiveCategory.USER_UNDERSTANDING,
            CognitiveCategory.COMMUNICATION,
        ],
        description="User preferences and communication style"
    ),
]


class Promoter:
    """
    Promotes high-value cognitive insights to project documentation.
    
    The promotion process:
    1. Find insights meeting promotion criteria
    2. Match insights to appropriate target files
    3. Format insights as concise rules
    4. Append to target files
    5. Mark insights as promoted
    """
    
    def __init__(self, project_dir: Optional[Path] = None,
                 reliability_threshold: float = DEFAULT_PROMOTION_THRESHOLD,
                 min_validations: int = DEFAULT_MIN_VALIDATIONS):
        self.project_dir = project_dir or Path.cwd()
        self.reliability_threshold = reliability_threshold
        self.min_validations = min_validations
    
    def _get_target_for_category(self, category: CognitiveCategory) -> Optional[PromotionTarget]:
        """Find the appropriate promotion target for a category."""
        for target in PROMOTION_TARGETS:
            if category in target.categories:
                return target
        return None
    
    def _format_insight_for_promotion(self, insight: CognitiveInsight) -> str:
        """Format an insight as a concise rule for documentation."""
        # Extract the core insight without verbose details
        rule = insight.insight
        
        # Add reliability indicator
        reliability_str = f"({insight.reliability:.0%} reliable, {insight.times_validated} validations)"
        
        # Add context if not generic
        if insight.context and insight.context not in ["General principle", "All interactions"]:
            context_note = f" *When: {insight.context[:50]}*"
        else:
            context_note = ""
        
        return f"- {rule}{context_note} {reliability_str}"
    
    def _ensure_section_exists(self, file_path: Path, section: str) -> str:
        """Ensure the target section exists in the file. Returns file content."""
        if not file_path.exists():
            # Create file with basic structure
            content = f"""# {file_path.stem}

{section}

*Auto-promoted insights from Spark*

"""
            file_path.write_text(content)
            return content
        
        content = file_path.read_text()
        
        if section not in content:
            # Add section at the end
            content += f"\n\n{section}\n\n*Auto-promoted insights from Spark*\n\n"
            file_path.write_text(content)
        
        return content
    
    def _append_to_section(self, file_path: Path, section: str, line: str):
        """Append a line to a specific section in a file."""
        content = self._ensure_section_exists(file_path, section)
        
        # Find the section and append after it
        section_idx = content.find(section)
        if section_idx == -1:
            return
        
        # Find the next section or end of file
        next_section = re.search(r'\n## ', content[section_idx + len(section):])
        if next_section:
            insert_idx = section_idx + len(section) + next_section.start()
        else:
            insert_idx = len(content)
        
        # Insert the new line before the next section
        new_content = content[:insert_idx].rstrip() + "\n" + line + "\n" + content[insert_idx:]
        file_path.write_text(new_content)
    
    def get_promotable_insights(self) -> List[Tuple[CognitiveInsight, str, PromotionTarget]]:
        """Get insights ready for promotion with their target files."""
        cognitive = get_cognitive_learner()
        promotable = []
        
        for key, insight in cognitive.insights.items():
            # Skip already promoted
            if insight.promoted:
                continue
            
            # Check criteria
            if insight.reliability < self.reliability_threshold:
                continue
            if insight.times_validated < self.min_validations:
                continue
            
            # Find target
            target = self._get_target_for_category(insight.category)
            if target:
                promotable.append((insight, key, target))
        
        return promotable
    
    def promote_insight(self, insight: CognitiveInsight, insight_key: str, 
                       target: PromotionTarget) -> bool:
        """Promote a single insight to its target file."""
        file_path = self.project_dir / target.filename
        
        try:
            # Format the insight
            formatted = self._format_insight_for_promotion(insight)
            
            # Append to target file
            self._append_to_section(file_path, target.section, formatted)
            
            # Mark as promoted
            cognitive = get_cognitive_learner()
            cognitive.mark_promoted(insight_key, target.filename)
            
            print(f"[SPARK] Promoted to {target.filename}: {insight.insight[:50]}...")
            return True
            
        except Exception as e:
            print(f"[SPARK] Promotion failed: {e}")
            return False
    
    def promote_all(self, dry_run: bool = False) -> Dict[str, int]:
        """Promote all eligible insights."""
        promotable = self.get_promotable_insights()
        stats = {"promoted": 0, "skipped": 0, "failed": 0}
        
        if not promotable:
            print("[SPARK] No insights ready for promotion")
            return stats
        
        print(f"[SPARK] Found {len(promotable)} insights ready for promotion")
        
        for insight, key, target in promotable:
            if dry_run:
                print(f"  [DRY RUN] Would promote to {target.filename}: {insight.insight[:50]}...")
                stats["skipped"] += 1
                continue
            
            if self.promote_insight(insight, key, target):
                stats["promoted"] += 1
            else:
                stats["failed"] += 1
        
        return stats
    
    def get_promotion_status(self) -> Dict:
        """Get status of promotions."""
        cognitive = get_cognitive_learner()
        promotable = self.get_promotable_insights()
        
        promoted = [i for i in cognitive.insights.values() if i.promoted]
        by_target = {}
        for insight in promoted:
            target = insight.promoted_to or "unknown"
            by_target[target] = by_target.get(target, 0) + 1
        
        return {
            "total_insights": len(cognitive.insights),
            "promoted_count": len(promoted),
            "ready_for_promotion": len(promotable),
            "by_target": by_target,
            "threshold": self.reliability_threshold,
            "min_validations": self.min_validations
        }


# ============= Singleton =============
_promoter: Optional[Promoter] = None

def get_promoter(project_dir: Optional[Path] = None) -> Promoter:
    """Get the promoter instance."""
    global _promoter
    if _promoter is None or (project_dir and _promoter.project_dir != project_dir):
        _promoter = Promoter(project_dir)
    return _promoter


# ============= Convenience Functions =============
def check_and_promote(project_dir: Optional[Path] = None, dry_run: bool = False) -> Dict[str, int]:
    """Check for promotable insights and promote them."""
    return get_promoter(project_dir).promote_all(dry_run)


def get_promotion_status(project_dir: Optional[Path] = None) -> Dict:
    """Get promotion status."""
    return get_promoter(project_dir).get_promotion_status()
