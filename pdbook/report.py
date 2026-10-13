"""The monthly report as one method chain, with checks inside the chain."""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from pdbook.enrich import enrich


def require(df: pd.DataFrame, test: Callable[[pd.DataFrame], bool], message: str) -> pd.DataFrame:
    """A step for `.pipe`: stop with `message` when `test(df)` is false, otherwise pass df on."""
    if not test(df):
        raise ValueError(message)
    return df


def monthly_report(calls: pd.DataFrame, subs: pd.DataFrame, cells: pd.DataFrame,
                   plans: pd.DataFrame) -> pd.DataFrame:
    """Calls, answer rate, billed minutes and revenue for each plan and home city."""
    enriched, _ = enrich(calls, subs, cells, plans)
    n_calls = len(calls)
    return (
        enriched
        .pipe(require, lambda d: d["call_id"].is_unique, "call_id is not unique")
        .assign(
            answered=lambda d: d["status"].eq("answered"),
            billed_min=lambda d: np.where(d["status"].eq("answered"),
                                          np.maximum(1, np.ceil(d["duration_s"] / 60)), 0),
        )
        .assign(revenue_eur=lambda d: (d["billed_min"] * d["rate_per_min_eur"]).round(2))
        .groupby(["plan", "home_city"], as_index=False)
        .agg(calls=("call_id", "size"), answered=("answered", "sum"),
             billed_min=("billed_min", "sum"), revenue_eur=("revenue_eur", "sum"))
        .pipe(require, lambda d: int(d["calls"].sum()) == n_calls, "the groups do not add up to the calls")
        .assign(answer_rate=lambda d: (d["answered"] / d["calls"]).round(3),
                revenue_eur=lambda d: d["revenue_eur"].round(2),
                billed_min=lambda d: d["billed_min"].astype("int64"))
        .sort_values(["plan", "home_city"])
        .reset_index(drop=True)
    )
