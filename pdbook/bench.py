"""Small timing helpers and one task written five ways."""
from __future__ import annotations

import time
from typing import Callable

import pandas as pd


def best_of(fn: Callable[[], object], repeat: int = 3) -> tuple[float, object]:
    """Seconds of the fastest of `repeat` runs, and the result of the last run."""
    best, result = float("inf"), None
    for _ in range(repeat):
        t0 = time.perf_counter()
        result = fn()
        best = min(best, time.perf_counter() - t0)
    return best, result


def replicate(df: pd.DataFrame, times: int) -> pd.DataFrame:
    """`times` copies of df stacked, with a unique call_id."""
    big = pd.concat([df] * times, ignore_index=True)
    big["call_id"] = range(len(big))
    return big


# The task: for each caller, the total talk minutes of answered calls longer than 60 seconds.

def task_iterrows(df: pd.DataFrame) -> pd.Series:
    total: dict[str, float] = {}
    for _, row in df.iterrows():
        if row["status"] == "answered" and row["duration_s"] > 60:
            total[row["caller"]] = total.get(row["caller"], 0.0) + row["duration_s"] / 60
    return pd.Series(total, name="talk_min").sort_index()


def task_itertuples(df: pd.DataFrame) -> pd.Series:
    total: dict[str, float] = {}
    for row in df.itertuples(index=False):
        if row.status == "answered" and row.duration_s > 60:
            total[row.caller] = total.get(row.caller, 0.0) + row.duration_s / 60
    return pd.Series(total, name="talk_min").sort_index()


def task_groupby_apply(df: pd.DataFrame) -> pd.Series:
    def one(g: pd.DataFrame) -> float:
        keep = g[(g["status"] == "answered") & (g["duration_s"] > 60)]
        return keep["duration_s"].sum() / 60

    out = df.groupby("caller")[["status", "duration_s"]].apply(one)
    return out[out > 0].rename("talk_min").sort_index()


def task_mask_groupby(df: pd.DataFrame) -> pd.Series:
    keep = df[(df["status"] == "answered") & (df["duration_s"] > 60)]
    return (keep.groupby("caller")["duration_s"].sum() / 60).rename("talk_min").sort_index()


def task_category(df: pd.DataFrame) -> pd.Series:
    d = df.assign(caller=df["caller"].astype("category"), status=df["status"].astype("category"))
    keep = d[(d["status"] == "answered") & (d["duration_s"] > 60)]
    out = keep.groupby("caller", observed=True)["duration_s"].sum() / 60
    out.index = out.index.astype(str)
    return out.rename("talk_min").sort_index()
