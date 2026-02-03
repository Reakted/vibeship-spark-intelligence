# X-Twitter MCP

A comprehensive, modular MCP (Model Context Protocol) server for X/Twitter with **permission-based access control**, Playwright article fetching, and 60+ tools.

## Features

- **Permission Profiles**: Choose what capabilities to enable (researcher, creator, manager, automation)
- **60+ Tools**: Comprehensive Twitter API coverage
- **Playwright Articles**: Properly renders X articles that require JavaScript
- **Engagement Metrics**: Search results include likes, retweets, replies
- **Rate Limiting**: Built-in rate limit management
- **Safe Defaults**: Starts in read-only researcher mode

---

## Quick Start

### Installation

```bash
# Basic installation
pip install x-twitter-mcp

# With article support (recommended)
pip install x-twitter-mcp[articles]
playwright install chromium
```

### From Source

```bash
cd mcp-servers/x-twitter-mcp
pip install -e .[articles]
playwright install chromium
```

### Configuration

Add to your Claude settings (`~/.claude.json` or project settings):

```json
{
  "mcpServers": {
    "x-twitter": {
      "type": "stdio",
      "command": "x-twitter-mcp-server",
      "env": {
        "TWITTER_API_KEY": "your_api_key",
        "TWITTER_API_SECRET": "your_api_secret",
        "TWITTER_ACCESS_TOKEN": "your_access_token",
        "TWITTER_ACCESS_TOKEN_SECRET": "your_access_token_secret",
        "TWITTER_BEARER_TOKEN": "your_bearer_token",
        "X_MCP_PROFILE": "researcher"
      }
    }
  }
}
```

---

## Profiles

Choose a profile based on your use case:

| Profile | Description | Tool Groups | Use Case |
|---------|-------------|-------------|----------|
| **researcher** | Read-only access | research, conversations | Monitoring, analysis, research |
| **creator** | Post & engage | + engage, publish | Content creation, audience growth |
| **manager** | Full account control | + social, lists | Account management, moderation |
| **automation** | Everything | + dms, account | Bots, full automation |
| **custom** | Pick your own | (you specify) | Fine-grained control |

### Setting a Profile

```bash
# Via environment variable
X_MCP_PROFILE=creator

# Via Claude config
"env": {
  "X_MCP_PROFILE": "creator"
}
```

### Custom Profile

Pick exactly which groups you want:

```bash
X_MCP_PROFILE=custom
X_MCP_GROUPS=research,engage,publish
```

---

## Tool Groups

### research (18 tools) - Safe, read-only

| Tool | Description |
|------|-------------|
| `search_twitter` | Search tweets with metrics |
| `search_articles` | Find tweets with X articles |
| `get_trends` | Trending topics |
| `get_article` | Fetch full article content (Playwright) |
| `get_user_profile` | User profile by ID |
| `get_user_by_screen_name` | User profile by @username |
| `get_user_tweets` | User's posted tweets |
| `get_liked_tweets` | Tweets a user liked |
| `get_user_followers` | User's followers |
| `get_user_following` | Who user follows |
| `get_tweet_details` | Full tweet info |
| `get_timeline` | Home timeline (For You) |
| `get_latest_timeline` | Following timeline |
| `get_user_mentions` | Mentions of a user |
| ... | |

### engage (9 tools) - Low risk, reversible

| Tool | Description |
|------|-------------|
| `favorite_tweet` | Like a tweet |
| `unfavorite_tweet` | Unlike a tweet |
| `bookmark_tweet` | Bookmark a tweet |
| `delete_bookmark` | Remove bookmark |
| `get_bookmarks` | View bookmarks |
| `retweet` | Retweet |
| `unretweet` | Remove retweet |
| `get_retweets` | Who retweeted |

### publish (7 tools) - Medium risk

| Tool | Description |
|------|-------------|
| `post_tweet` | Post a tweet |
| `delete_tweet` | Delete a tweet |
| `quote_tweet` | Quote tweet |
| `create_thread` | Post a thread |
| `create_poll_tweet` | Create poll |

### social (8 tools) - Medium-high risk

| Tool | Description |
|------|-------------|
| `follow_user` | Follow |
| `unfollow_user` | Unfollow |
| `block_user` | Block |
| `unblock_user` | Unblock |
| `mute_user` | Mute |
| `unmute_user` | Unmute |
| `get_blocked_users` | List blocked |
| `get_muted_users` | List muted |

### conversations (5 tools) - Safe

| Tool | Description |
|------|-------------|
| `get_conversation` | Full thread |
| `get_replies` | Replies to tweet |
| `get_quote_tweets` | Quotes of tweet |
| `hide_reply` | Hide a reply |
| `unhide_reply` | Unhide a reply |

### lists (14 tools) - Low risk

| Tool | Description |
|------|-------------|
| `create_list` | Create a list |
| `delete_list` | Delete a list |
| `update_list` | Update list details |
| `get_list` | Get list info |
| `get_list_tweets` | Tweets from list |
| `get_list_members` | List members |
| `add_list_member` | Add to list |
| `remove_list_member` | Remove from list |
| `follow_list` | Follow a list |
| `unfollow_list` | Unfollow list |
| `pin_list` | Pin list |
| `unpin_list` | Unpin list |

### dms (3 tools) - High risk

| Tool | Description |
|------|-------------|
| `send_dm` | Send direct message |
| `get_dm_conversations` | List DM conversations |
| `get_dm_events` | Messages in a DM |

### account (1 tool) - High risk

| Tool | Description |
|------|-------------|
| `get_me` | Get your own profile |

---

## Advanced Configuration

### Disable Specific Tools

```bash
X_MCP_PROFILE=creator
X_MCP_DISABLED_TOOLS=delete_tweet,create_poll_tweet
```

### Force-Enable Specific Tools

```bash
X_MCP_PROFILE=researcher
X_MCP_ENABLED_TOOLS=favorite_tweet,bookmark_tweet
```

### Full Example

```json
{
  "mcpServers": {
    "x-twitter": {
      "type": "stdio",
      "command": "x-twitter-mcp-server",
      "env": {
        "TWITTER_API_KEY": "...",
        "TWITTER_API_SECRET": "...",
        "TWITTER_ACCESS_TOKEN": "...",
        "TWITTER_ACCESS_TOKEN_SECRET": "...",
        "TWITTER_BEARER_TOKEN": "...",
        "X_MCP_PROFILE": "custom",
        "X_MCP_GROUPS": "research,engage,conversations",
        "X_MCP_DISABLED_TOOLS": "get_trends"
      }
    }
  }
}
```

---

## Article Fetching

X/Twitter articles require JavaScript to render. This MCP uses Playwright:

```python
# Automatically extracts full article content
result = await get_article("https://x.com/user/status/123456789")
# Returns: {title, author, content, url}
```

**Without Playwright installed:**
```json
{"error": "Playwright not installed. Run: pip install playwright && playwright install chromium"}
```

---

## Rate Limits

Built-in rate limiting to prevent API errors:

| Action Type | Limit | Window |
|-------------|-------|--------|
| Tweet actions | 300 | 15 minutes |
| DM actions | 1000 | 15 minutes |
| Follow actions | 400 | 24 hours |
| Like actions | 1000 | 24 hours |
| List actions | 300 | 15 minutes |

---

## Use Cases

### Research / Monitoring
```bash
X_MCP_PROFILE=researcher
```
- Search and analyze tweets
- Monitor trends
- Track user activity
- Read articles
- No risk of accidental posts

### Content Creator
```bash
X_MCP_PROFILE=creator
```
- Post tweets and threads
- Engage with audience (likes, retweets)
- No follow/block actions (prevents accidents)

### Account Manager
```bash
X_MCP_PROFILE=manager
```
- Full account control
- Manage followers (follow/block/mute)
- Create and manage lists
- No DM access

### Full Automation
```bash
X_MCP_PROFILE=automation
```
- Everything enabled
- DM support
- Use with caution

---

## API Requirements

You need Twitter API credentials:
1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Create a project and app
3. Generate API keys and tokens
4. Set the environment variables

Required credentials:
- `TWITTER_API_KEY`
- `TWITTER_API_SECRET`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_TOKEN_SECRET`
- `TWITTER_BEARER_TOKEN`

---

## HTTP Server Mode

For cloud deployments:

```bash
# Start HTTP server (default port 8081)
x-twitter-mcp-http

# Custom port
PORT=8080 x-twitter-mcp-http
```

---

## Credits

Built on [x-twitter-mcp-server](https://github.com/rafaljanicki/x-twitter-mcp-server) by Rafal Janicki, enhanced with:
- Permission-based access control
- 60+ tools (vs ~20 original)
- Playwright article fetching
- Thread creation
- Lists, DMs, social actions
- Comprehensive metrics

## License

MIT License
