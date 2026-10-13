"""Chapter 22: flatten the call traces and check them against the call records."""
import pandas as pd

from pdbook.io import load_calls
from pdbook.traces import call_summary, events_table, read_traces

records = read_traces()
events = events_table(records)
summary = call_summary(events, [r["call_id"] for r in records])
status = load_calls().set_index("call_id").loc[summary.index, "status"]

print(f"{len(records)} traces -> {len(events)} events, {int(summary['established'].sum())} established calls")
print(pd.crosstab(status, summary["established"]).to_string())
no_events = summary[summary["n_events"] == 0]
print("traces with no events:", len(no_events), status.loc[no_events.index].value_counts().to_dict())
assert (status[summary["established"]] == "answered").all()
