# Labor Market Intelligence MCP Server

## Install

```bash
git clone https://github.com/Schoobert/mcp-labor-market
cd mcp-labor-market
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/database.py   # builds the SQLite database from raw data files — run once
```

Then wire it into Claude Desktop (see [How to try it](#how-to-try-it) below).

---

## [Loom walkthrough coming soon]

---

## What this is and what problem it solves

When I'm job searching, I keep hitting the same dead end. I have a question like "what roles are close to what I do now?" or "is this salary offer competitive?" — and there's no fast, structured place to get an answer. Job boards give me listings, not insight. Salary sites give me ranges, not context.

This is a server that plugs into Claude Desktop and gives Claude access to real labor market data: occupation descriptions, employment projections, skill profiles, and wage benchmarks. When I ask Claude a career question, it can now look up actual numbers instead of guessing.

The data comes from two public government sources. The Bureau of Labor Statistics (BLS) publishes employment projections every two years, including how many jobs exist in each field, how many are expected by 2034, and what the median salary is. O*NET — the Department of Labor's occupational database — describes what skills, knowledge, and preparation each job actually requires. I downloaded both datasets and cached them locally. Claude is reading from a database on my machine, not making live API calls.

---

## How to try it

You need Python 3.11 or later and [Claude Desktop](https://claude.ai/download) installed. This takes about five minutes.

**Step 1 — Clone and install**

```bash
git clone https://github.com/Schoobert/mcp-labor-market
cd mcp-labor-market
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Step 2 — Build the local database**

```bash
python src/database.py
```

This reads the raw data files in `data/raw/` and writes a SQLite database to `data/cached/labor_market.db`. It only needs to run once.

**Step 3 — Add the server to Claude Desktop**

Open Claude Desktop. Go to **Settings → Developer → Edit Config**. Add this block inside the `"mcpServers"` object:

```json
"labor-market-intelligence": {
  "command": "/absolute/path/to/mcp-labor-market/.venv/bin/python",
  "args": ["/absolute/path/to/mcp-labor-market/src/server.py"]
}
```

Replace both paths with the real absolute paths on your machine (`pwd` in the project root will show you). Save the file, then fully quit and reopen Claude Desktop.

**Step 4 — Try it**

Start a new conversation and paste this in:

> I'm a Trust and Safety analyst thinking about my next career move. What roles are most adjacent to mine, and how do the salaries compare?

Claude will call `find_adjacent_roles` and `benchmark_compensation` automatically. You can also try:

> Compare the skills required for a Trust and Safety analyst and a Policy Manager. Where do they overlap and where are the gaps?

You should see Claude reasoning over real O*NET skill importance scores and BLS wage data.

---

## How it works

### Architecture

The server has three layers, each with a single responsibility:

- **`server.py`** — registers six tools with the MCP SDK using FastMCP decorators. Every tool docstring is written as routing instructions for an AI agent, not human documentation. This layer does nothing except receive calls and delegate them.
- **`tools.py`** — all business logic. Each function connects to SQLite, resolves occupation identifiers (handling SOC codes, partial codes, and plain-English job titles), runs queries, and returns a plain dictionary.
- **`database.py`** — schema definition and data loaders. Parses O*NET TSV files and the BLS Excel workbook into a normalized SQLite schema at setup time. Does not run at query time.

The data flow is: raw files → `database.py` → SQLite → `tools.py` → `server.py` → Claude Desktop.

### Data sources and vintage

| Source | What it provides | Vintage |
|--------|-----------------|---------|
| BLS Employment Projections, Table 1.2 (`occupation.xlsx`) | Employment 2024 and 2034, projected change %, annual job openings, median annual wage 2024 | 2024–2034 projection cycle |
| O*NET Occupation Data (`Occupation Data.txt`) | SOC codes, occupation titles, descriptions | Cached at project build time |
| O*NET Skills (`Essential Skills.txt`) | Skill importance and level scores (IM scale, 1–5) per occupation | Cached at project build time |
| O*NET Related Occupations (`Related Occupations.txt`) | Relatedness tiers linking occupation pairs | Cached at project build time |
| O*NET Job Zones (`Job Zones.txt`) | Preparation level (1–5) per occupation | Cached at project build time |
| O*NET Job Titles (`Job Titles.txt`) | Alternate and common job posting titles per SOC code | Cached at project build time |

The data does not update automatically. Everything reflects the state of these files when the database was built.

### Tool surface design rationale

I designed six tools. The scoping of each one was deliberate.

**`get_occupation_outlook`** takes a single occupation and returns everything needed to evaluate it: growth projections, wages, education requirements, and current employment size. It's one tool, not six fields across separate tools, because these fields all answer the same question: "is this a good role to pursue?" Splitting them would force Claude to make multiple round trips for what is always a single user intent.

**`compare_skills_demand`** takes exactly two occupations — no more. The use case is always "how does role A compare to role B?" — a binary comparison. Accepting a list would add interface complexity without serving a real agent use case. The output is two ranked skill lists side by side, which is the form a language model can reason over directly without additional tool calls.

**`benchmark_compensation`** is deliberately separate from the outlook tool. Compensation questions ("is this salary competitive?") are a distinct user intent from growth questions ("is this field growing?"). Keeping them separate lets Claude pick the right tool for the actual question asked. The benchmark group — the five closest related occupations by O*NET tier — is not an arbitrary selection; it's the occupations the Department of Labor itself considers most related to the target role.

**`find_adjacent_roles`** is purely about career mapping. It returns ten roles ordered by O*NET relatedness tier, with job zone and wage included so Claude can reason about both the direction and the difficulty of each transition in a single response. I capped it at ten because that's enough for a meaningful career conversation and keeps the output size manageable for a model context window.

**`save_research_session`** and **`list_past_sessions`** are the write layer. They exist to solve one specific problem: a multi-session job search means Claude forgets what you looked at last time. These two tools give Claude a place to persist findings and retrieve them in later conversations. The write schema is narrow — summary, occupations researched, key findings — because the goal is recall scaffolding, not a database replacement. The read tools can re-fetch underlying data; the write tools just need to preserve enough context to re-enter a prior research thread.

---

## What I learned

**MCP changes the tool design problem fundamentally.** When you design a tool for a human, you optimize for discoverability, learnability, and error tolerance. When you design a tool for an AI agent, you optimize for unambiguous intent signals and predictable output shape. The docstrings on these tools are not documentation — they're routing instructions. I rewrote them multiple times because a vague docstring doesn't just confuse users; it causes the model to call the wrong tool or skip the right one entirely.

**Stateful tool design is harder than the schema suggests.** The write tools look simple — two functions, a handful of columns. But they forced me to think carefully about what a "session" means to an AI agent (not a login session — a research thread), what the right unit of persistence is (summary plus key findings, not a full query log), and how to write the `list_past_sessions` docstring so Claude knows when to call it unprompted, without me explicitly asking. The hard part wasn't the SQLite schema; it was the triggering language.

**Resolving occupation identifiers across two schemas is a real problem.** O*NET uses six-decimal SOC codes (`11-1011.00`). BLS uses five-character codes (`11-1011`). Users might type a job title, a partial title, or a variant name from a job posting. I ended up with a five-step resolution chain in `_resolve_soc` — exact O*NET match, BLS-format match, exact job title match, substring title match, substring job title match — to handle the realistic range of inputs without returning errors on reasonable queries. In production, this would need fuzzy matching and probably a disambiguation step when multiple occupations match.

**Cached data is a deliberate constraint, not a limitation.** This server makes no live API calls at runtime. That's intentional: latency stays near zero, there are no rate limits, and the tool surface is fully deterministic. The tradeoff is that the data ages. For a portfolio project demonstrating tool design and MCP architecture, that tradeoff is correct. For a production system serving real job seekers, it would not be.

---

## Production Considerations

Several things would need to change before this could serve real users at scale:

- **Data freshness pipeline** — O*NET publishes new releases roughly twice a year; BLS updates employment projections on a two-year cycle. A production system would need a scheduled job that checks for new releases, downloads the updated files, and rebuilds the database without downtime.
- **Occupation disambiguation** — the current `_resolve_soc` function does substring matching and returns the first hit. A production resolver would need fuzzy matching with a ranked candidate list and a disambiguation step when multiple occupations match a query.
- **Live job posting signal** — this server has no current listings data. Real market signal (what's actually being hired for right now, at what volume) would require a job posting API or crawl pipeline with its own ingestion layer.
- **Multi-user session storage** — the write tools write to a single SQLite file on the local filesystem. Multi-user deployments would need per-user session isolation, authentication, and a proper database backend.
- **Error observability** — the server currently returns `{"error": str(e)}` on failures. A production deployment would need structured error logging, alerting, and monitoring to catch data quality issues and tool failures.

---

## Technical Details

**Runtime dependencies:** `mcp==1.27.2` (MCP Python SDK, FastMCP), `openpyxl==3.1.5` (BLS Excel parsing), SQLite (Python stdlib)

**Python version:** 3.11+

**Database schema:**

| Table | Contents |
|-------|----------|
| `occupations` | O*NET SOC codes, titles, descriptions |
| `skills` | Skill importance and level scores by occupation and scale |
| `related_occupations` | O*NET relatedness tiers linking occupation pairs |
| `job_zones` | Preparation level (1–5) per occupation |
| `education` | Education requirements by category and scale |
| `job_titles` | Alternate and job posting titles per SOC code |
| `compensation` | BLS employment projections and wage data (2024–2034) |
| `research_sessions` | Write tool persistence; created at server startup |

**Running the server:**
```bash
python src/server.py
```
Stdio transport. Consumed by Claude Desktop via the MCP config entry.

**Building the database:**
```bash
python src/database.py
```
Reads `data/raw/`, writes `data/cached/labor_market.db`. Run once at setup.
