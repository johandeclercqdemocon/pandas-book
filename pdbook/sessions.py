"""Group calls of one subscriber into sessions: a new session starts after a quiet gap."""
from __future__ import annotations

import pandas as pd


def sessionize(calls: pd.DataFrame, gap: str = "30min") -> pd.DataFrame:
    """Add `session` (1, 2, ... for each caller) and `session_id` ("S0001-001") to every call.

    A call starts a new session when the time since the START of the previous call of the
    same caller is greater than `gap`. A gap of exactly `gap` stays in the same session.
    The input can be in any row order. The result is sorted by caller and start, with the
    same columns plus the two new ones.
    """
    out = calls.sort_values(["caller", "start", "call_id"], kind="stable").reset_index(drop=True)
    since_previous = out.groupby("caller")["start"].diff()
    starts_new = since_previous.isna() | (since_previous > pd.Timedelta(gap))
    out["session"] = starts_new.groupby(out["caller"]).cumsum().astype("int64")
    out["session_id"] = out["caller"] + "-" + out["session"].astype(str).str.zfill(3)
    return out


def session_table(sessions: pd.DataFrame) -> pd.DataFrame:
    """One row for each session."""
    return (
        sessions.groupby("session_id", sort=False)
        .agg(caller=("caller", "first"), first_start=("start", "min"), last_start=("start", "max"),
             calls=("call_id", "size"), talk_s=("duration_s", "sum"))
        .reset_index()
    )
