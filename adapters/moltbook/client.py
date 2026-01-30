#!/usr/bin/env python3
"""
Moltbook API Client

A Python client for interacting with the Moltbook social network for AI agents.
https://moltbook.com - "The front page of the agent internet"

Usage:
    from adapters.moltbook.client import MoltbookClient

    client = MoltbookClient(api_key="your-api-key")

    # Create a post
    post = client.create_post(
        submolt="spark-insights",
        title="Learning from 1000 tool calls",
        body="Here's what I learned..."
    )

    # Comment on a post
    comment = client.create_comment(
        post_id="abc123",
        body="Great insight! I've noticed similar patterns."
    )
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

# ============= Configuration =============
API_BASE_URL = "https://www.moltbook.com/api/v1"
CONFIG_DIR = Path.home() / ".spark" / "moltbook"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


class ContentType(str, Enum):
    TEXT = "text"
    LINK = "link"


class FeedType(str, Enum):
    HOT = "hot"
    NEW = "new"
    TOP = "top"
    RISING = "rising"


class VoteType(str, Enum):
    UP = "up"
    DOWN = "down"


@dataclass
class Agent:
    """A Moltbook agent profile."""
    id: str
    name: str
    karma: int = 0
    description: str = ""
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    post_count: int = 0
    comment_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            karma=data.get("karma", 0),
            description=data.get("description", ""),
            avatar_url=data.get("avatar_url"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            post_count=data.get("post_count", 0),
            comment_count=data.get("comment_count", 0),
        )


@dataclass
class Post:
    """A Moltbook post."""
    id: str
    title: str
    body: str = ""
    url: Optional[str] = None
    content_type: ContentType = ContentType.TEXT
    submolt: str = ""
    author_id: str = ""
    author_name: str = ""
    upvotes: int = 0
    downvotes: int = 0
    comment_count: int = 0
    created_at: Optional[datetime] = None
    is_pinned: bool = False

    @property
    def karma(self) -> int:
        return self.upvotes - self.downvotes

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Post":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            body=data.get("body", ""),
            url=data.get("url"),
            content_type=ContentType(data.get("content_type", "text")),
            submolt=data.get("submolt", ""),
            author_id=data.get("author_id", ""),
            author_name=data.get("author_name", ""),
            upvotes=data.get("upvotes", 0),
            downvotes=data.get("downvotes", 0),
            comment_count=data.get("comment_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            is_pinned=data.get("is_pinned", False),
        )


@dataclass
class Comment:
    """A Moltbook comment."""
    id: str
    body: str
    post_id: str
    parent_id: Optional[str] = None
    author_id: str = ""
    author_name: str = ""
    upvotes: int = 0
    downvotes: int = 0
    created_at: Optional[datetime] = None
    replies: List["Comment"] = field(default_factory=list)

    @property
    def karma(self) -> int:
        return self.upvotes - self.downvotes

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Comment":
        return cls(
            id=data.get("id", ""),
            body=data.get("body", ""),
            post_id=data.get("post_id", ""),
            parent_id=data.get("parent_id"),
            author_id=data.get("author_id", ""),
            author_name=data.get("author_name", ""),
            upvotes=data.get("upvotes", 0),
            downvotes=data.get("downvotes", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            replies=[Comment.from_dict(r) for r in data.get("replies", [])],
        )


@dataclass
class Submolt:
    """A Moltbook community (submolt)."""
    id: str
    name: str
    description: str = ""
    subscriber_count: int = 0
    post_count: int = 0
    created_at: Optional[datetime] = None
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    is_subscribed: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Submolt":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            subscriber_count=data.get("subscriber_count", 0),
            post_count=data.get("post_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            avatar_url=data.get("avatar_url"),
            banner_url=data.get("banner_url"),
            is_subscribed=data.get("is_subscribed", False),
        )


@dataclass
class RateLimitInfo:
    """Rate limit information from API response."""
    requests_remaining: int = 100
    posts_remaining: int = 1
    comments_remaining: int = 50
    retry_after_seconds: int = 0

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> "RateLimitInfo":
        return cls(
            requests_remaining=int(headers.get("X-RateLimit-Remaining", 100)),
            posts_remaining=int(headers.get("X-RateLimit-Posts-Remaining", 1)),
            comments_remaining=int(headers.get("X-RateLimit-Comments-Remaining", 50)),
            retry_after_seconds=int(headers.get("Retry-After", 0)),
        )


class MoltbookError(Exception):
    """Base exception for Moltbook API errors."""
    def __init__(self, message: str, status_code: int = 0, response: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class RateLimitError(MoltbookError):
    """Raised when rate limit is exceeded."""
    def __init__(self, retry_after_seconds: int = 60, limit_type: str = "requests"):
        super().__init__(
            f"Rate limit exceeded for {limit_type}. Retry after {retry_after_seconds} seconds.",
            status_code=429
        )
        self.retry_after_seconds = retry_after_seconds
        self.limit_type = limit_type


class AuthenticationError(MoltbookError):
    """Raised when authentication fails."""
    pass


class NotFoundError(MoltbookError):
    """Raised when a resource is not found."""
    pass


class MoltbookClient:
    """
    Client for interacting with the Moltbook API.

    The Moltbook platform is a social network for AI agents where they can
    share posts, comment, vote, and participate in communities (submolts).

    Rate Limits:
        - 100 requests/minute overall
        - 1 post per 30 minutes
        - 50 comments per hour
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = API_BASE_URL,
        timeout: int = 30,
    ):
        """
        Initialize the Moltbook client.

        Args:
            api_key: Bearer token for authentication. If not provided,
                     will try to load from credentials file or env var.
            base_url: API base URL (default: https://moltbook.com/api/v1)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._api_key = api_key or self._load_api_key()
        self._rate_limit_info = RateLimitInfo()
        self._last_post_time: Optional[float] = None

    def _load_api_key(self) -> Optional[str]:
        """Load API key from credentials file or environment."""
        # Try environment variable first
        key = os.environ.get("MOLTBOOK_API_KEY")
        if key:
            return key

        # Try credentials file
        if CREDENTIALS_FILE.exists():
            try:
                data = json.loads(CREDENTIALS_FILE.read_text())
                return data.get("api_key")
            except Exception:
                pass

        return None

    def save_credentials(self, api_key: str, agent_id: Optional[str] = None):
        """Save credentials to local file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"api_key": api_key}
        if agent_id:
            data["agent_id"] = agent_id
        CREDENTIALS_FILE.write_text(json.dumps(data, indent=2))
        self._api_key = api_key

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        require_auth: bool = True,
    ) -> Dict[str, Any]:
        """Make a request to the API."""
        if require_auth and not self._api_key:
            raise AuthenticationError("No API key configured. Run `spark moltbook register` first.")

        url = f"{self.base_url}{endpoint}"
        if params:
            url = f"{url}?{urlencode(params)}"

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Spark-Intelligence/1.0",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        body = json.dumps(data).encode() if data else None

        request = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(request, timeout=self.timeout) as response:
                # Update rate limit info from headers
                self._rate_limit_info = RateLimitInfo.from_headers(
                    dict(response.headers)
                )

                response_data = json.loads(response.read().decode())
                return response_data

        except HTTPError as e:
            status_code = e.code
            try:
                error_data = json.loads(e.read().decode())
            except Exception:
                error_data = {}

            if status_code == 401:
                raise AuthenticationError("Invalid API key", status_code, error_data)
            elif status_code == 404:
                raise NotFoundError("Resource not found", status_code, error_data)
            elif status_code == 429:
                retry_after = int(e.headers.get("Retry-After", 60))
                limit_type = error_data.get("limit_type", "requests")
                raise RateLimitError(retry_after, limit_type)
            else:
                raise MoltbookError(
                    error_data.get("message", f"HTTP {status_code}"),
                    status_code,
                    error_data,
                )

        except URLError as e:
            raise MoltbookError(f"Network error: {e.reason}")

    # ============= Registration =============

    def register(self, name: str, description: str) -> Dict[str, str]:
        """
        Register a new agent on Moltbook.

        Args:
            name: Agent display name
            description: Agent description/bio

        Returns:
            Dict with api_key, agent_id, claim_url, and verification_code

        Note:
            After registration, the human owner must verify ownership
            by posting the verification code on Twitter/X.
        """
        response = self._request("POST", "/agents/register", {
            "name": name,
            "description": description,
        }, require_auth=False)

        # Parse nested response format
        agent_data = response.get("agent", {})
        api_key = agent_data.get("api_key")
        agent_id = agent_data.get("id")

        # Save credentials automatically
        if api_key:
            self.save_credentials(api_key=api_key, agent_id=agent_id)

        # Return flattened response for easier use
        return {
            "api_key": api_key,
            "agent_id": agent_id,
            "claim_url": agent_data.get("claim_url"),
            "verification_code": agent_data.get("verification_code"),
            "profile_url": agent_data.get("profile_url"),
            "tweet_template": response.get("tweet_template"),
            "status": response.get("status"),
            "raw": response,
        }

    def check_verification_status(self) -> Dict[str, Any]:
        """Check if the agent has been verified."""
        return self._request("GET", "/agents/status")

    # ============= Profile =============

    def get_my_profile(self) -> Agent:
        """Get the current agent's profile."""
        response = self._request("GET", "/agents/me")
        return Agent.from_dict(response)

    def get_agent(self, agent_id: str) -> Agent:
        """Get another agent's profile."""
        response = self._request("GET", f"/agents/{agent_id}")
        return Agent.from_dict(response)

    def update_profile(
        self,
        description: Optional[str] = None,
        avatar_data: Optional[bytes] = None,
    ) -> Agent:
        """Update the agent's profile."""
        data = {}
        if description is not None:
            data["description"] = description
        # Avatar upload would need multipart/form-data handling
        response = self._request("PATCH", "/agents/me", data)
        return Agent.from_dict(response)

    # ============= Posts =============

    def create_post(
        self,
        submolt: str,
        title: str,
        body: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Post:
        """
        Create a new post.

        Args:
            submolt: Community to post in (e.g., "spark-insights")
            title: Post title
            body: Post body text (for text posts)
            url: Link URL (for link posts)

        Returns:
            The created Post

        Raises:
            RateLimitError: If posting too frequently (1 post per 30 min)
        """
        # Check cooldown
        if self._last_post_time:
            elapsed = time.time() - self._last_post_time
            if elapsed < 1800:  # 30 minutes
                remaining = int(1800 - elapsed)
                raise RateLimitError(remaining, "posts")

        data = {
            "submolt": submolt,
            "title": title,
        }
        if body:
            data["body"] = body
            data["content_type"] = "text"
        if url:
            data["url"] = url
            data["content_type"] = "link"

        response = self._request("POST", "/posts", data)
        self._last_post_time = time.time()
        return Post.from_dict(response)

    def get_post(self, post_id: str) -> Post:
        """Get a specific post by ID."""
        response = self._request("GET", f"/posts/{post_id}")
        return Post.from_dict(response)

    def delete_post(self, post_id: str) -> bool:
        """Delete a post (only own posts)."""
        self._request("DELETE", f"/posts/{post_id}")
        return True

    def get_feed(
        self,
        feed_type: FeedType = FeedType.HOT,
        submolt: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Post]:
        """
        Get posts from a feed.

        Args:
            feed_type: Type of feed (hot, new, top, rising)
            submolt: Filter to specific community (optional)
            limit: Max posts to return (default 25)
            offset: Pagination offset

        Returns:
            List of Posts
        """
        params = {
            "sort": feed_type.value,
            "limit": limit,
            "offset": offset,
        }

        if submolt:
            endpoint = f"/submolts/{submolt}/posts"
        else:
            endpoint = "/posts"

        response = self._request("GET", endpoint, params=params)
        return [Post.from_dict(p) for p in response.get("posts", [])]

    def get_my_feed(self, limit: int = 25, offset: int = 0) -> List[Post]:
        """Get personalized feed from subscriptions and follows."""
        params = {"limit": limit, "offset": offset}
        response = self._request("GET", "/feed", params=params)
        return [Post.from_dict(p) for p in response.get("posts", [])]

    # ============= Comments =============

    def create_comment(
        self,
        post_id: str,
        body: str,
        parent_id: Optional[str] = None,
    ) -> Comment:
        """
        Create a comment on a post or reply to another comment.

        Args:
            post_id: The post to comment on
            body: Comment text
            parent_id: Optional parent comment ID for replies

        Returns:
            The created Comment
        """
        data = {
            "post_id": post_id,
            "body": body,
        }
        if parent_id:
            data["parent_id"] = parent_id

        response = self._request("POST", "/comments", data)
        return Comment.from_dict(response)

    def get_comments(
        self,
        post_id: str,
        sort: str = "best",
        limit: int = 50,
    ) -> List[Comment]:
        """Get comments for a post."""
        params = {"sort": sort, "limit": limit}
        response = self._request("GET", f"/posts/{post_id}/comments", params=params)
        return [Comment.from_dict(c) for c in response.get("comments", [])]

    def delete_comment(self, comment_id: str) -> bool:
        """Delete a comment (only own comments)."""
        self._request("DELETE", f"/comments/{comment_id}")
        return True

    # ============= Voting =============

    def vote_post(self, post_id: str, vote_type: VoteType) -> Dict[str, int]:
        """Upvote or downvote a post."""
        response = self._request("POST", f"/posts/{post_id}/vote", {
            "vote": vote_type.value,
        })
        return response

    def vote_comment(self, comment_id: str, vote_type: VoteType) -> Dict[str, int]:
        """Upvote or downvote a comment."""
        response = self._request("POST", f"/comments/{comment_id}/vote", {
            "vote": vote_type.value,
        })
        return response

    # ============= Submolts (Communities) =============

    def get_submolt(self, name: str) -> Submolt:
        """Get information about a submolt."""
        response = self._request("GET", f"/submolts/{name}")
        return Submolt.from_dict(response)

    def create_submolt(
        self,
        name: str,
        description: str,
    ) -> Submolt:
        """Create a new submolt community."""
        response = self._request("POST", "/submolts", {
            "name": name,
            "description": description,
        })
        return Submolt.from_dict(response)

    def subscribe(self, submolt: str) -> bool:
        """Subscribe to a submolt."""
        self._request("POST", f"/submolts/{submolt}/subscribe")
        return True

    def unsubscribe(self, submolt: str) -> bool:
        """Unsubscribe from a submolt."""
        self._request("DELETE", f"/submolts/{submolt}/subscribe")
        return True

    def get_subscriptions(self) -> List[Submolt]:
        """Get list of subscribed submolts."""
        response = self._request("GET", "/agents/me/subscriptions")
        return [Submolt.from_dict(s) for s in response.get("submolts", [])]

    # ============= Following =============

    def follow(self, agent_id: str) -> bool:
        """Follow another agent."""
        self._request("POST", f"/agents/{agent_id}/follow")
        return True

    def unfollow(self, agent_id: str) -> bool:
        """Unfollow an agent."""
        self._request("DELETE", f"/agents/{agent_id}/follow")
        return True

    def get_following(self) -> List[Agent]:
        """Get list of agents being followed."""
        response = self._request("GET", "/agents/me/following")
        return [Agent.from_dict(a) for a in response.get("agents", [])]

    # ============= Search =============

    def search(
        self,
        query: str,
        search_type: str = "all",  # all, posts, agents, submolts
        limit: int = 25,
    ) -> Dict[str, List]:
        """
        Search Moltbook.

        Args:
            query: Search query
            search_type: What to search (all, posts, agents, submolts)
            limit: Max results

        Returns:
            Dict with posts, agents, and/or submolts lists
        """
        params = {
            "q": query,
            "type": search_type,
            "limit": limit,
        }
        response = self._request("GET", "/search", params=params)

        result = {}
        if "posts" in response:
            result["posts"] = [Post.from_dict(p) for p in response["posts"]]
        if "agents" in response:
            result["agents"] = [Agent.from_dict(a) for a in response["agents"]]
        if "submolts" in response:
            result["submolts"] = [Submolt.from_dict(s) for s in response["submolts"]]

        return result

    # ============= Rate Limit Info =============

    @property
    def rate_limit_info(self) -> RateLimitInfo:
        """Get current rate limit information."""
        return self._rate_limit_info

    def can_post(self) -> bool:
        """Check if we can post (respecting 30-min cooldown)."""
        if not self._last_post_time:
            return True
        return time.time() - self._last_post_time >= 1800

    def time_until_can_post(self) -> int:
        """Seconds until next post is allowed."""
        if not self._last_post_time:
            return 0
        remaining = 1800 - (time.time() - self._last_post_time)
        return max(0, int(remaining))


# ============= Convenience Functions =============

def get_client() -> MoltbookClient:
    """Get a configured Moltbook client (loads credentials automatically)."""
    return MoltbookClient()


def is_registered() -> bool:
    """Check if Spark is registered on Moltbook."""
    return CREDENTIALS_FILE.exists()
