"""Chapter 9: enrich the calls, and show that a duplicate key is refused."""
import pandas as pd
from pandas.errors import MergeError

from pdbook.enrich import enrich
from pdbook.io import load_calls, load_cells, load_plans, load_subscribers

calls, subs, cells, plans = load_calls(), load_subscribers(), load_cells(), load_plans()
enriched, report = enrich(calls, subs, cells, plans)
print(f"{len(calls):,d} calls -> {len(enriched):,d} rows, {enriched.shape[1]} columns")
print("unmatched keys:", report)
print(f"on-net calls: {int(enriched['on_net'].sum()):,d} ({enriched['on_net'].mean():.1%})")

dirty = pd.concat([subs, subs.head(10)], ignore_index=True)
try:
    enrich(calls, dirty, cells, plans)
except MergeError as error:
    print("duplicate subscriber ids are refused:", type(error).__name__)
