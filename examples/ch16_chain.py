"""Chapter 16: the monthly report as one chain, and the checks that guard it."""
import numpy as np
import pandas as pd

from pdbook.io import load_calls, load_cells, load_plans, load_subscribers
from pdbook.rating import rate_vector
from pdbook.report import monthly_report

calls, subs, cells, plans = load_calls(), load_subscribers(), load_cells(), load_plans()
report = monthly_report(calls, subs, cells, plans)
print(report.head(8).to_string(index=False))
print("...", len(report), "rows")

independent = float(rate_vector(calls, subs, plans).sum())
assert np.isclose(report["revenue_eur"].sum(), independent)
assert int(report["calls"].sum()) == len(calls)
pd.testing.assert_frame_equal(report, monthly_report(calls.sample(frac=1, random_state=1), subs, cells, plans))
print(f"\nrevenue {report['revenue_eur'].sum():,.2f} EUR = independent computation {independent:,.2f}; order-independent: True")
