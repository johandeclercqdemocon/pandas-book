"""Chapter 20: the monthly report in SQL and in pandas, and the proof that they agree."""
import pandas as pd

from pdbook.io import load_calls, load_cells, load_plans, load_subscribers
from pdbook.report import monthly_report
from pdbook.sqlbridge import MONTHLY_REPORT_SQL, build_database, monthly_report_sql

conn = build_database()
sql_report = monthly_report_sql(conn)
pandas_report = monthly_report(load_calls(), load_subscribers(), load_cells(), load_plans())
pd.testing.assert_frame_equal(sql_report, pandas_report[sql_report.columns])

print(MONTHLY_REPORT_SQL.strip().splitlines()[0], "...")
print(sql_report.head(5).to_string(index=False))
print(f"\n{len(sql_report)} rows; SQL and pandas agree in every cell and every dtype")
