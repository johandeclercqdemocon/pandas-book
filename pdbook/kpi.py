"""Hourly cell KPIs in local time, with a count of the samples behind each hour."""
from __future__ import annotations

import pandas as pd


def hourly_kpi(kpi: pd.DataFrame, tz: str = "Europe/Brussels", full_hour: int = 12) -> pd.DataFrame:
    """One row for each cell and local hour.

    Steps: drop repeated (ts, cell_id) rows, convert to `tz`, take the mean of each hour.
    `n` is the number of 5-minute samples in the hour (12 for a full hour). `complete` is
    True when n >= full_hour. The local hour is the true clock hour, so on the day that
    summer time ends there are 25 of them.
    """
    unique = kpi.drop_duplicates(["ts", "cell_id"])
    local = unique.assign(ts=unique["ts"].dt.tz_convert(tz)).set_index("ts")
    hourly = (
        local.groupby("cell_id")[["prb_util_pct", "drop_rate_pct", "throughput_mbps"]]
        .resample("1h")
        .mean()
    )
    n = local.groupby("cell_id")["prb_util_pct"].resample("1h").count().rename("n")
    out = hourly.join(n).reset_index()
    out["complete"] = out["n"] >= full_hour
    return out
