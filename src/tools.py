import sqlite3

from database import DB_PATH


def _resolve_soc(query: str, conn: sqlite3.Connection) -> str:
    """Resolve a SOC code or occupation title string to an O*NET SOC code.

    Resolution order:
    1. Exact O*NET code match (e.g. "11-1011.00")
    2. BLS-format code match (e.g. "11-1011") → returns first O*NET variant
    3. Exact job_title match (case-insensitive)
    4. Substring match on occupation title
    5. Substring match on job_titles
    """
    row = conn.execute(
        "SELECT soc_code FROM occupations WHERE soc_code = ?", (query,)
    ).fetchone()
    if row:
        return row[0]

    row = conn.execute(
        "SELECT soc_code FROM occupations WHERE SUBSTR(soc_code, 1, 7) = ? LIMIT 1", (query,)
    ).fetchone()
    if row:
        return row[0]

    row = conn.execute(
        "SELECT soc_code FROM job_titles WHERE LOWER(job_title) = LOWER(?)", (query,)
    ).fetchone()
    if row:
        return row[0]

    row = conn.execute(
        "SELECT soc_code FROM occupations WHERE LOWER(title) LIKE LOWER(?)", (f"%{query}%",)
    ).fetchone()
    if row:
        return row[0]

    row = conn.execute(
        "SELECT soc_code FROM job_titles WHERE LOWER(job_title) LIKE LOWER(?)", (f"%{query}%",)
    ).fetchone()
    if row:
        return row[0]

    raise ValueError(f"Could not resolve occupation: {query!r}")


def _tier_order() -> str:
    return "CASE relatedness_tier WHEN 'Primary-Short' THEN 1 WHEN 'Primary-Long' THEN 2 ELSE 3 END"


def get_occupation_outlook(soc_code_or_title: str) -> dict:
    """Return outlook data for a single occupation.

    Includes title, description, job zone, typical education, employment
    projections (2024–2034), annual job openings, and median annual wage.
    Compensation data is sourced from BLS Line item rows only.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        soc = _resolve_soc(soc_code_or_title, conn)
        bls = soc[:7]

        occ = conn.execute(
            "SELECT title, description FROM occupations WHERE soc_code = ?", (soc,)
        ).fetchone()

        jz = conn.execute(
            "SELECT job_zone FROM job_zones WHERE soc_code = ?", (soc,)
        ).fetchone()

        comp = conn.execute(
            "SELECT typical_education, employment_2024, employment_2034, "
            "employment_change_pct, annual_job_openings, median_annual_wage_2024 "
            "FROM compensation WHERE soc_code = ? AND occupation_type = 'Line item'",
            (bls,),
        ).fetchone()

        return {
            "soc_code": soc,
            "title": occ["title"].strip(),
            "description": occ["description"],
            "job_zone": jz["job_zone"] if jz else None,
            "typical_education": comp["typical_education"] if comp else None,
            "employment_2024": comp["employment_2024"] if comp else None,
            "employment_2034": comp["employment_2034"] if comp else None,
            "employment_change_pct": comp["employment_change_pct"] if comp else None,
            "annual_job_openings": comp["annual_job_openings"] if comp else None,
            "median_annual_wage_2024": comp["median_annual_wage_2024"] if comp else None,
        }


def compare_skills_demand(
    soc_code_or_title_1: str, soc_code_or_title_2: str
) -> dict:
    """Return the top 10 skills by importance (Scale ID=IM) for two occupations side by side.

    Use this to compare skill profiles and identify overlaps or gaps between roles.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        soc1 = _resolve_soc(soc_code_or_title_1, conn)
        soc2 = _resolve_soc(soc_code_or_title_2, conn)

        def top_skills(soc: str) -> list[dict]:
            rows = conn.execute(
                "SELECT element_name, data_value FROM skills "
                "WHERE soc_code = ? AND scale_id = 'IM' "
                "ORDER BY data_value DESC LIMIT 10",
                (soc,),
            ).fetchall()
            return [{"skill": r["element_name"], "importance": r["data_value"]} for r in rows]

        title1 = conn.execute(
            "SELECT title FROM occupations WHERE soc_code = ?", (soc1,)
        ).fetchone()
        title2 = conn.execute(
            "SELECT title FROM occupations WHERE soc_code = ?", (soc2,)
        ).fetchone()

        return {
            "occupation_1": {
                "soc_code": soc1,
                "title": title1["title"].strip(),
                "top_skills": top_skills(soc1),
            },
            "occupation_2": {
                "soc_code": soc2,
                "title": title2["title"].strip(),
                "top_skills": top_skills(soc2),
            },
        }


def benchmark_compensation(soc_code_or_title: str) -> dict:
    """Return median annual wage for an occupation plus its top 5 related occupations.

    Use this to assess whether a role's compensation is above or below comparable
    occupations. BLS compensation data, Line item rows only.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        soc = _resolve_soc(soc_code_or_title, conn)
        bls = soc[:7]

        comp = conn.execute(
            "SELECT title, median_annual_wage_2024 FROM compensation "
            "WHERE soc_code = ? AND occupation_type = 'Line item'",
            (bls,),
        ).fetchone()

        tier_order = _tier_order()
        related = conn.execute(
            f"SELECT ro.related_soc_code, c.title, c.median_annual_wage_2024 "
            f"FROM related_occupations ro "
            f"JOIN compensation c ON SUBSTR(ro.related_soc_code, 1, 7) = c.soc_code "
            f"WHERE ro.soc_code = ? AND c.occupation_type = 'Line item' "
            f"GROUP BY c.soc_code "
            f"ORDER BY {tier_order}, ro.idx "
            f"LIMIT 5",
            (soc,),
        ).fetchall()

        return {
            "soc_code": soc,
            "title": comp["title"].strip() if comp else None,
            "median_annual_wage_2024": comp["median_annual_wage_2024"] if comp else None,
            "related_occupations": [
                {
                    "soc_code": r["related_soc_code"],
                    "title": r["title"].strip(),
                    "median_annual_wage_2024": r["median_annual_wage_2024"],
                }
                for r in related
            ],
        }


def find_adjacent_roles(soc_code_or_title: str) -> dict:
    """Return the top 10 related occupations by relatedness tier and index.

    Includes title, job zone, and median annual wage for each adjacent role.
    Use this to map career transitions, lateral moves, or upward paths.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        soc = _resolve_soc(soc_code_or_title, conn)

        tier_order = _tier_order()
        rows = conn.execute(
            f"SELECT ro.related_soc_code, o.title, jz.job_zone, c.median_annual_wage_2024 "
            f"FROM related_occupations ro "
            f"JOIN occupations o ON o.soc_code = ro.related_soc_code "
            f"LEFT JOIN job_zones jz ON jz.soc_code = ro.related_soc_code "
            f"LEFT JOIN compensation c "
            f"    ON SUBSTR(ro.related_soc_code, 1, 7) = c.soc_code "
            f"    AND c.occupation_type = 'Line item' "
            f"WHERE ro.soc_code = ? "
            f"ORDER BY {tier_order}, ro.idx "
            f"LIMIT 10",
            (soc,),
        ).fetchall()

        occ = conn.execute(
            "SELECT title FROM occupations WHERE soc_code = ?", (soc,)
        ).fetchone()

        return {
            "soc_code": soc,
            "title": occ["title"].strip(),
            "adjacent_roles": [
                {
                    "soc_code": r["related_soc_code"],
                    "title": r["title"].strip(),
                    "job_zone": r["job_zone"],
                    "median_annual_wage_2024": r["median_annual_wage_2024"],
                }
                for r in rows
            ],
        }
