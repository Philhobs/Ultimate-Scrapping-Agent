# Ultimate Scrapping Agent

An intelligent web scraping agent with automatic tier escalation, powered by the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Part of a mono-repo architecture designed to host multiple AI agents sharing common infrastructure.

## Features

- **4-Tier Auto-Escalation** — Starts with basic HTTP, automatically escalates through stealth headers, headless browser (Playwright), and proxy rotation when blocked
- **Block Detection** — Pattern-matches Cloudflare challenges, reCAPTCHA, hCaptcha, rate limiting, and generic bot detection (detect-only, never solves)
- **Structured Extraction** — CSS selector-based parsing for text, links, tables, and arbitrary elements via BeautifulSoup
- **4 MCP Tools** — `fetch_url`, `parse_html`, `extract_data`, `escalate_tier` — all available to the Claude agent during its reasoning loop
- **REST API** — FastAPI endpoints to trigger scrapes, retrieve results, and check health
- **Persistent History** — Async SQLite storage of all scrape jobs and results via SQLModel

## Architecture

```
Claude_testing/
├── config/
│   └── scraper_agent.yaml            # Agent config (tiers, rate limits, model)
├── common/                           # Shared infrastructure for all agents
│   ├── agent_base.py                 # Abstract base class wrapping ClaudeSDKClient
│   ├── config_loader.py              # YAML + env var config (AGENT_* prefix)
│   ├── retry.py                      # Tenacity-based async retry
│   ├── rate_limiter.py               # Token-bucket rate limiter
│   ├── persistence/
│   │   ├── models.py                 # SQLModel base with timestamps
│   │   └── database.py              # Async SQLite engine
│   └── api/
│       └── app_factory.py            # FastAPI factory with DB lifespan
├── agents/
│   └── web_scraper/
│       ├── agent.py                  # WebScraperAgent(AgentBase)
│       ├── main.py                   # Uvicorn entrypoint (port 8001)
│       ├── tools/                    # MCP tools
│       │   ├── fetch_url.py          # Tiered fetching with auto-escalation
│       │   ├── parse_html.py         # BeautifulSoup extraction
│       │   ├── extract_data.py       # LLM-powered structured extraction
│       │   └── escalate_tier.py      # Manual tier control
│       ├── scraping/
│       │   ├── tiers.py              # Tier enum + TierManager state machine
│       │   ├── http_client.py        # Tier 1-2: httpx async
│       │   ├── browser_client.py     # Tier 3: Playwright headless
│       │   ├── proxy_pool.py         # Tier 4: proxy rotation
│       │   ├── user_agents.py        # UA string rotation (20 realistic UAs)
│       │   └── anti_detect.py        # CAPTCHA/block detection
│       ├── parsing/
│       │   └── html_cleaner.py       # BS4 cleaning + extraction
│       ├── persistence/
│       │   ├── models.py             # ScrapeJob, ScrapeResult ORM
│       │   └── repository.py         # Async database queries
│       └── api/
│           ├── router.py             # POST /scrape, GET /sessions, GET /health
│           ├── schemas.py            # Pydantic request/response models
│           └── dependencies.py       # FastAPI dependency injection
└── tests/
    └── agents/web_scraper/
        ├── conftest.py               # Shared fixtures
        ├── test_tiers.py             # TierManager escalation tests
        ├── test_http_client.py       # Mocked HTTP client tests
        └── test_tools.py             # Parsing, detection, and MCP tool tests
```

## Scraping Tiers

| Tier | Name | Method | When Used |
|------|------|--------|-----------|
| 1 | BASIC | Plain `httpx` GET | Default starting point |
| 2 | STEALTH | `httpx` with realistic headers, UA rotation, cookies | After Tier 1 is blocked |
| 3 | BROWSER | Playwright headless Chromium | JS-rendered pages or Tier 2 blocked |
| 4 | PROXY | Rotating proxy pool + stealth headers | Opt-in, requires proxy URLs |

The `TierManager` state machine tracks attempts per tier and auto-escalates after configurable retries.

## Quick Start

### Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
git clone https://github.com/Philhobs/Ultimate-Scrapping-Agent.git
cd Ultimate-Scrapping-Agent

pip install -e ".[dev]"

# For Tier 3 (browser) support
playwright install chromium
```

### Configuration

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

Agent settings live in `config/scraper_agent.yaml`. Override any value with environment variables using the `AGENT_` prefix:

```bash
export AGENT_SCRAPER_MAX_TIER=2        # Limit to HTTP-only tiers
export AGENT_SCRAPER_RATE_LIMIT=10     # Requests per second
```

### Run the API Server

```bash
python -m agents.web_scraper.main
```

The server starts on `http://localhost:8001`.

### API Usage

**Scrape a page:**

```bash
curl -X POST http://localhost:8001/api/v1/scraper/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Extract all book titles and prices",
    "url": "https://books.toscrape.com/",
    "output_format": "json",
    "schema_fields": ["title", "price"]
  }'
```

**Retrieve a past session:**

```bash
curl http://localhost:8001/api/v1/scraper/sessions/{session_id}
```

**Health check:**

```bash
curl http://localhost:8001/api/v1/scraper/health
```

## Tests

```bash
pytest tests/ -v
```

```
44 passed in 0.49s
```

Tests cover:
- TierManager escalation logic (12 tests)
- HTTP client with mocked responses (4 tests)
- HTML cleaner and extraction (8 tests)
- Anti-bot block detection (7 tests)
- MCP tool integration (13 tests)

## MCP Tools Reference

| Tool | Description |
|------|-------------|
| `fetch_url` | Fetch a URL with automatic tier escalation. Accepts optional `cookies`, `force_tier`, `max_tier` |
| `parse_html` | Extract data from HTML. Modes: `text`, `links`, `tables`, `elements` (with CSS selector) |
| `extract_data` | Prepare HTML for structured extraction with a JSON schema. The agent reasons over the content |
| `escalate_tier` | Manual tier control: `escalate`, `set`, `reset`, `status` |

## Tech Stack

- **Agent Framework:** [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)
- **HTTP:** httpx (async, HTTP/2)
- **Browser:** Playwright (headless Chromium)
- **Parsing:** BeautifulSoup4 + lxml
- **API:** FastAPI + Uvicorn
- **Database:** SQLModel + aiosqlite (async SQLite)
- **Config:** PyYAML + python-dotenv
- **Retry:** Tenacity
- **Logging:** structlog

## License

MIT
