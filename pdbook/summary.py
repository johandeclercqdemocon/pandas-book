"""One row per subscriber, from the call records."""
from __future__ import annotations

import pandas as pd


def subscriber_summary(calls: pd.DataFrame, subs: pd.DataFrame) -> pd.DataFrame:
    """Calls, answer rate, talk time, cells used and first/last call, for every subscriber.

    A subscriber with no calls is kept, with zeros, so the table always has one row per subscriber.
    """
    flagged = calls.assign(
        answered=calls["status"].eq("answered"),
        failed=calls["status"].eq("failed"),
        talk_min=calls["duration_s"].fillna(0) / 60,
    )
    g = flagged.groupby("caller")
    per = g.agg(
        calls=("call_id", "size"),
        answered=("answered", "sum"),
        failed=("failed", "sum"),
        talk_min=("talk_min", "sum"),
        cells=("cell_id", "nunique"),
        first_call=("start", "min"),
        last_call=("start", "max"),
    )
    out = subs.set_index("subscriber_id")[["plan", "city"]].join(per)
    for col in ("calls", "answered", "failed"):
        out[col] = out[col].fillna(0).astype("int64")
    out["talk_min"] = out["talk_min"].fillna(0.0).round(1)
    out["cells"] = out["cells"].fillna(0).astype("int64")
    out["answer_rate"] = (out["answered"] / out["calls"]).where(out["calls"] > 0).round(3)
    return out.reset_index()
