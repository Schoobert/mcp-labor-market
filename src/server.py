from mcp.server.fastmcp import FastMCP

import tools

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


if __name__ == "__main__":
    mcp.run()
