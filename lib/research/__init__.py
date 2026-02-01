"""
Domain Research System

Researches what mastery looks like in a domain BEFORE
trying to learn from observation. Sets intent for learning.

"You can't recognize excellence if you don't know what it looks like."
"""

from .mastery import MasteryResearcher, DomainMastery, research_domain
from .intents import IntentSetter, DomainIntent, set_learning_intent

__all__ = [
    'MasteryResearcher',
    'DomainMastery',
    'research_domain',
    'IntentSetter',
    'DomainIntent',
    'set_learning_intent',
]
