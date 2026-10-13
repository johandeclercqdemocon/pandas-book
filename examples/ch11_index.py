"""Chapter 11: audit the index of several tables."""
import pandas as pd

from pdbook.indexcheck import index_audit
from pdbook.io import load_calls

calls = load_calls()
tables = {
    "calls (default index)": calls,
    "calls by call_id": calls.set_index("call_id"),
    "calls by call_id, sorted": calls.set_index("call_id").sort_index(),
    "two copies stacked": pd.concat([calls.head(3), calls.head(3)]),
    "calls by caller, start": calls.set_index(["caller", "start"]),
}
for name, table in tables.items():
    a = index_audit(table)
    print(f"{name:26s} unique={a['unique']!s:5} sorted={a['sorted']!s:5} dup_labels={a['duplicate_labels']} levels={a['levels']}")
