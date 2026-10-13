"""Call traces: one JSON object for each call, with a list of signalling events inside."""
from __future__ import annotations

import json
import pathlib

import pandas as pd

from pdbook.datasets import DATA


def read_traces(path: str | pathlib.Path | None = None) -> list[dict]:
    """One dict for each line of a JSON-lines file."""
    path = DATA / "traces.jsonl" if path is None else path
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def events_table(records: list[dict]) -> pd.DataFrame:
    """One row for each event, with the call_id, caller, cell and codec of its call.

    A call with no events has no row. A call with no `meta` has NaN for cell and codec.
    """
    flat = pd.json_normalize(records, record_path="events",
                             meta=["call_id", "caller", ["meta", "cell"], ["meta", "codec"]], errors="ignore")
    flat = flat.rename(columns={"meta.cell": "cell", "meta.codec": "codec"})
    flat["call_id"] = flat["call_id"].astype("int64")
    columns = ["call_id", "caller", "cell", "codec", "t_ms", "type", "code"]
    return flat[columns].sort_values(["call_id", "t_ms"], kind="stable").reset_index(drop=True)


def call_summary(events: pd.DataFrame, call_ids: list[int]) -> pd.DataFrame:
    """One row for each call id: events, time to ringing, time to answer, last response code.

    Calls with no events are kept, with 0 events and missing times.
    """
    responses = events[events["type"] == "RESPONSE"]
    out = pd.DataFrame(index=pd.Index(call_ids, name="call_id"))
    out["n_events"] = events.groupby("call_id").size().reindex(out.index, fill_value=0)
    out["ring_ms"] = responses[responses["code"] == 180].groupby("call_id")["t_ms"].min()
    out["answer_ms"] = responses[responses["code"] == 200].groupby("call_id")["t_ms"].min()
    out["final_code"] = responses.groupby("call_id")["code"].last()
    out["established"] = out["answer_ms"].notna()
    return out
