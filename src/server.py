from mcp.server.fastmcp import FastMCP

import tools
from database import create_research_sessions_table

create_research_sessions_table()

mcp = FastMCP("labor-market-intelligence")


@mcp.tool()
def get_occupation_outlook(soc_code_or_title: str) -> dict:
    """Return employment outlook and compensation data for a single occupation.

    Use this when the user asks about job growth, hiring projections, wages, or
    education requirements for a specific role. Accepts an O*NET SOC code
    (e.g. "11-1011.00"), a BLS SOC code (e.g. "11-1011"), or a job title
    (e.g. "Chief Executives"). Returns title, description, job zone, typical
    education, employment in 2024 and 2034, projected change percent, annual
    job openings, and median annual wage.
    """
    try:
        return tools.get_occupation_outlook(soc_code_or_title)
    except ValueError as e:
        return {"error": str(e)}


@mcp.tool()
def compare_skills_demand(
    soc_code_or_title_1: str, soc_code_or_title_2: str
) -> dict:
    """Compare the top 10 most important skills for two occupations side by side.

    Use this when the user wants to understand skill overlap between roles,
    identify transferable skills for a career transition, or evaluate skill
    gaps between a current and target role. Accepts SOC codes or job titles
    for each occupation. Returns ranked skill importance scores (O*NET IM
    scale, 1–5) for both occupations in a single response.
    """
    try:
        return tools.compare_skills_demand(soc_code_or_title_1, soc_code_or_title_2)
    except ValueError as e:
        return {"error": str(e)}


@mcp.tool()
def benchmark_compensation(soc_code_or_title: str) -> dict:
    """Return median annual wage for an occupation benchmarked against its closest related roles.

    Use this when the user asks whether a salary offer is competitive, wants to
    understand the compensation range across a career cluster, or needs to
    compare pay between related occupations. Returns the occupation's median
    annual wage plus wages for the top 5 most-related occupations by O*NET
    relatedness tier.
    """
    try:
        return tools.benchmark_compensation(soc_code_or_title)
    except ValueError as e:
        return {"error": str(e)}


@mcp.tool()
def find_adjacent_roles(soc_code_or_title: str) -> dict:
    """Return the 10 most related occupations for a given role with job zone and wage data.

    Use this when the user asks about career paths, lateral moves, stepping-stone
    roles, or what jobs they could transition into from their current occupation.
    Results are ordered by O*NET relatedness tier (Primary-Short first, then
    Primary-Long, then Supplemental) and include job zone and median annual wage
    for each adjacent role.
    """
    try:
        return tools.find_adjacent_roles(soc_code_or_title)
    except ValueError as e:
        return {"error": str(e)}


@mcp.tool()
def save_research_session(
    summary: str, occupations_researched: str, key_findings: str
) -> dict:
    """Save the current research session to persistent storage after completing a task.

    Call this after you have answered a meaningful research question — for example,
    after comparing occupations, benchmarking compensation, or mapping a career
    transition — and the findings are worth preserving for future reference. Pass a
    plain-English summary of what was researched, a comma-separated list of occupation
    titles or SOC codes examined, and the most important factual findings from the
    session. Returns a confirmation with the assigned session_id.
    """
    return tools.save_research_session(summary, occupations_researched, key_findings)


@mcp.tool()
def list_past_sessions(limit: int = 10) -> dict:
    """Return recent research sessions saved in this server's history.

    Call this when the user references prior research ("what did we look at before",
    "last time we compared roles", "what have I already researched"), wants to build
    on earlier findings, or asks for a summary of past activity. Returns session_id,
    timestamp, occupations researched, and summary for each session — omits full
    key_findings to keep the list scannable. Use get_occupation_outlook or other
    read tools to re-fetch details once you identify the relevant session.
    """
    return tools.list_past_sessions(limit)


if __name__ == "__main__":
    mcp.run()
