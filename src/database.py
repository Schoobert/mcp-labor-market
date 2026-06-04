import csv
import sqlite3
from pathlib import Path

import openpyxl

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
DB_PATH = Path(__file__).parent.parent / "data" / "cached" / "labor_market.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS occupations (
    soc_code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS skills (
    soc_code TEXT NOT NULL,
    element_id TEXT NOT NULL,
    element_name TEXT NOT NULL,
    scale_id TEXT NOT NULL,
    data_value REAL,
    recommend_suppress TEXT,
    not_relevant TEXT,
    PRIMARY KEY (soc_code, element_id, scale_id)
);

CREATE TABLE IF NOT EXISTS related_occupations (
    soc_code TEXT NOT NULL,
    related_soc_code TEXT NOT NULL,
    relatedness_tier TEXT,
    idx INTEGER,
    PRIMARY KEY (soc_code, related_soc_code)
);

CREATE TABLE IF NOT EXISTS job_zones (
    soc_code TEXT PRIMARY KEY,
    job_zone INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS education (
    soc_code TEXT NOT NULL,
    element_id TEXT NOT NULL,
    element_name TEXT NOT NULL,
    scale_id TEXT NOT NULL,
    category INTEGER,
    data_value REAL,
    PRIMARY KEY (soc_code, element_id, scale_id, category)
);

CREATE TABLE IF NOT EXISTS job_titles (
    soc_code TEXT NOT NULL,
    job_title TEXT NOT NULL,
    short_title TEXT,
    sources TEXT,
    PRIMARY KEY (soc_code, job_title)
);

CREATE TABLE IF NOT EXISTS compensation (
    soc_code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    occupation_type TEXT,
    employment_2024 REAL,
    employment_2034 REAL,
    employment_change_numeric REAL,
    employment_change_pct REAL,
    annual_job_openings REAL,
    median_annual_wage_2024 REAL,
    typical_education TEXT,
    work_experience TEXT,
    typical_training TEXT
);

CREATE TABLE IF NOT EXISTS research_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    summary TEXT NOT NULL,
    occupations_researched TEXT NOT NULL,
    key_findings TEXT NOT NULL
);
"""


def _float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _read_tsv(filename):
    with open(RAW_DIR / filename, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _load_occupations(conn):
    rows = _read_tsv("Occupation Data.txt")
    conn.executemany(
        "INSERT OR REPLACE INTO occupations VALUES (?, ?, ?)",
        [(r["O*NET-SOC Code"], r["Title"], r["Description"]) for r in rows],
    )
    return len(rows)


def _load_skills(conn):
    rows = _read_tsv("Essential Skills.txt")
    conn.executemany(
        "INSERT OR REPLACE INTO skills VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                r["O*NET-SOC Code"],
                r["Element ID"],
                r["Element Name"],
                r["Scale ID"],
                _float(r["Data Value"]),
                r["Recommend Suppress"],
                r["Not Relevant"],
            )
            for r in rows
        ],
    )
    return len(rows)


def _load_related_occupations(conn):
    rows = _read_tsv("Related Occupations.txt")
    conn.executemany(
        "INSERT OR REPLACE INTO related_occupations VALUES (?, ?, ?, ?)",
        [
            (
                r["O*NET-SOC Code"],
                r["Related O*NET-SOC Code"],
                r["Relatedness Tier"],
                _int(r["Index"]),
            )
            for r in rows
        ],
    )
    return len(rows)


def _load_job_zones(conn):
    rows = _read_tsv("Job Zones.txt")
    conn.executemany(
        "INSERT OR REPLACE INTO job_zones VALUES (?, ?)",
        [(r["O*NET-SOC Code"], _int(r["Job Zone"])) for r in rows],
    )
    return len(rows)


def _load_education(conn):
    rows = _read_tsv("Education.txt")
    conn.executemany(
        "INSERT OR REPLACE INTO education VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                r["O*NET-SOC Code"],
                r["Element ID"],
                r["Element Name"],
                r["Scale ID"],
                _int(r["Category"]),
                _float(r["Data Value"]),
            )
            for r in rows
        ],
    )
    return len(rows)


def _load_compensation(conn):
    wb = openpyxl.load_workbook(RAW_DIR / "occupation.xlsx", read_only=True, data_only=True)
    ws = wb["Table 1.2"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    data = rows[2:]  # row 0 = title, row 1 = headers
    conn.executemany(
        "INSERT OR REPLACE INTO compensation VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                r[1],           # soc_code (BLS NEM code, e.g. "11-1011")
                r[0],           # title
                r[2],           # occupation_type
                _float(r[3]),   # employment_2024 (thousands)
                _float(r[4]),   # employment_2034 (thousands)
                _float(r[7]),   # employment_change_numeric (thousands)
                _float(r[8]),   # employment_change_pct
                _float(r[10]),  # annual_job_openings (thousands)
                _float(r[11]),  # median_annual_wage_2024
                r[12],          # typical_education
                r[13],          # work_experience
                r[14],          # typical_training
            )
            for r in data
            if r[1] is not None
        ],
    )
    return len(data)


def _load_job_titles(conn):
    rows = _read_tsv("Job Titles.txt")
    conn.executemany(
        "INSERT OR REPLACE INTO job_titles VALUES (?, ?, ?, ?)",
        [
            (r["O*NET-SOC Code"], r["Job Title"], r["Short Title"], r["Source(s)"])
            for r in rows
        ],
    )
    return len(rows)


_LOADERS = [
    ("occupations", _load_occupations),
    ("skills", _load_skills),
    ("related_occupations", _load_related_occupations),
    ("job_zones", _load_job_zones),
    ("education", _load_education),
    ("job_titles", _load_job_titles),
    ("compensation", _load_compensation),
]


def create_research_sessions_table():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS research_sessions ("
            "session_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "timestamp TEXT NOT NULL, "
            "summary TEXT NOT NULL, "
            "occupations_researched TEXT NOT NULL, "
            "key_findings TEXT NOT NULL"
            ")"
        )


def build_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    for table, loader in _LOADERS:
        count = loader(conn)
        print(f"  {table}: {count} rows")
    conn.commit()
    conn.close()
    create_research_sessions_table()
    print(f"Database written to {DB_PATH}")


if __name__ == "__main__":
    build_database()
