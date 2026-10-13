"""The same report in SQL and in pandas, over SQLite (in the Python standard library)."""
from __future__ import annotations

import sqlite3

import pandas as pd

from pdbook.io import load_calls, load_cells, load_plans, load_subscribers

MONTHLY_REPORT_SQL = """
SELECT s.plan                                              AS plan,
       s.city                                              AS home_city,
       COUNT(*)                                            AS calls,
       SUM(c.status = 'answered')                          AS answered,
       SUM(CASE WHEN c.status = 'answered'
                THEN CAST(MAX(1, CEIL(c.duration_s / 60.0)) AS INTEGER) ELSE 0 END)  AS billed_min,
       ROUND(SUM(CASE WHEN c.status = 'answered'
                THEN ROUND(MAX(1, CEIL(c.duration_s / 60.0)) * p.rate_per_min_eur, 2)
                ELSE 0 END), 2)                            AS revenue_eur,
       ROUND(1.0 * SUM(c.status = 'answered') / COUNT(*), 3) AS answer_rate
FROM calls c
JOIN subscribers s ON s.subscriber_id = c.caller
JOIN plans p       ON p.plan = s.plan
GROUP BY s.plan, s.city
ORDER BY s.plan, s.city
"""


def build_database(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    """Write the four tables into SQLite. `start` is stored as ISO text, as SQLite has no timestamp type."""
    conn = conn or sqlite3.connect(":memory:")
    calls = load_calls().assign(start=lambda d: d["start"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    calls.to_sql("calls", conn, index=False, if_exists="replace")
    load_subscribers().assign(signup_date=lambda d: d["signup_date"].dt.strftime("%Y-%m-%d")) \
        .to_sql("subscribers", conn, index=False, if_exists="replace")
    load_cells().to_sql("cells", conn, index=False, if_exists="replace")
    load_plans().to_sql("plans", conn, index=False, if_exists="replace")
    return conn


def monthly_report_sql(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(MONTHLY_REPORT_SQL, conn)
