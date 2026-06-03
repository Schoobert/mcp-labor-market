# Build 5: Labor Market Intelligence MCP Server

Global session rules live in ~/.claude/CLAUDE.md. Read that first.

## What this build does
A Python MCP server that gives Claude Desktop structured access to curated,
cached public labor market data (BLS, O*NET, public job posting datasets).
Exposes read tools for querying occupation outlook, skill demand, compensation
benchmarks, and adjacent roles — plus write tools for saving and retrieving
research sessions. Designed to demonstrate stateful tool design and agent-first
tool surface design.

## Who it's for
Portfolio artifact targeting T&S, AI governance, and TPM hiring managers.
Also genuinely useful for the active job search.

## Stack
- Python
- MCP Python SDK (mcp)
- SQLite (persistence layer for write tools)
- BLS, O*NET, and public job posting dataset (cached locally, no live scraping)

## Build-specific constraints
- Tools are designed for agent consumption, not human consumption. Every tool
  name and description must be written so an AI agent can decide correctly
  when to call it.
- Data is cached locally with vintage documented. No live scraping, no external
  API calls at runtime.
- Write tools (save_research_session, list_past_sessions) are built last, after
  all read tools are working and tested.
- Minimum structure only. Do not add source accuracy drafting protocol.