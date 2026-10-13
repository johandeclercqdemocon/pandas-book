"""Calls per weekday and hour: the wide grid, its long form, and the way back."""
from __future__ import annotations

import pandas as pd

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def traffic_grid(calls: pd.DataFrame, tz: str = "Europe/Brussels") -> pd.DataFrame:
    """7 rows (Mon..Sun) x 24 columns (0..23): the number of calls started in each local hour."""
    local = calls["start"].dt.tz_convert(tz)
    grid = (
        pd.DataFrame({"weekday": local.dt.dayofweek, "hour": local.dt.hour})
        .assign(n=1)
        .pivot_table(index="weekday", columns="hour", values="n", aggfunc="sum", fill_value=0)
        .reindex(index=range(7), columns=range(24), fill_value=0)
        .astype("int64")
    )
    grid.index = pd.Index(WEEKDAYS, name="weekday")
    grid.columns.name = "hour"
    return grid


def to_long(grid: pd.DataFrame) -> pd.DataFrame:
    """One row for each (weekday, hour). The hour is an integer, not text."""
    long = grid.reset_index().melt(id_vars="weekday", var_name="hour", value_name="calls")
    long["hour"] = long["hour"].astype("int64")
    return long


def to_wide(long: pd.DataFrame) -> pd.DataFrame:
    wide = long.pivot(index="weekday", columns="hour", values="calls").reindex(WEEKDAYS)
    return wide
