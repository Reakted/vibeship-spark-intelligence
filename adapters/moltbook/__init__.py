"""
Moltbook Adapter for Spark Intelligence

This module provides integration between Spark and Moltbook,
the social network for AI agents.

Components:
- client: API client for interacting with Moltbook
- agent: Autonomous agent behavior for engagement
- heartbeat: Background daemon for periodic activity

Usage:
    from adapters.moltbook import get_client, SparkMoltbookAgent

    # Get API client
    client = get_client()

    # Get agent for autonomous behavior
    agent = SparkMoltbookAgent()
    agent.heartbeat()
"""

from adapters.moltbook.client import (
    MoltbookClient,
    get_client,
    is_registered,
    Agent,
    Post,
    Comment,
    Submolt,
    FeedType,
    VoteType,
    ContentType,
    MoltbookError,
    RateLimitError,
    AuthenticationError,
)
from adapters.moltbook.agent import SparkMoltbookAgent, AgentState

__all__ = [
    # Client
    "MoltbookClient",
    "get_client",
    "is_registered",
    # Data types
    "Agent",
    "Post",
    "Comment",
    "Submolt",
    # Enums
    "FeedType",
    "VoteType",
    "ContentType",
    # Errors
    "MoltbookError",
    "RateLimitError",
    "AuthenticationError",
    # Agent
    "SparkMoltbookAgent",
    "AgentState",
]
