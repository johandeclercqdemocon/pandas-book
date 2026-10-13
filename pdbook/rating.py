"""Price each call, three ways. All three must give the same bill.

Rule: only answered calls are billed. The billed time is the duration rounded UP to whole minutes,
with a minimum of one minute. The price per minute depends on the plan of the caller.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _lookups(subs: pd.DataFrame, plans: pd.DataFrame) -> tuple[dict, dict]:
    plan_of = dict(zip(subs["subscriber_id"], subs["plan"]))
    rate_of = dict(zip(plans["plan"], plans["rate_per_min_eur"]))
    return plan_of, rate_of


def rate_loop(calls: pd.DataFrame, subs: pd.DataFrame, plans: pd.DataFrame) -> pd.Series:
    """One Python loop over iterrows(). The slowest way, and the one people write first."""
    plan_of, rate_of = _lookups(subs, plans)
    out = []
    for _, row in calls.iterrows():
        if row["status"] != "answered":
            out.append(0.0)
            continue
        minutes = max(1, math.ceil(row["duration_s"] / 60))
        out.append(round(minutes * rate_of[plan_of[row["caller"]]], 2))
    return pd.Series(out, index=calls.index, name="cost_eur")


def rate_apply(calls: pd.DataFrame, subs: pd.DataFrame, plans: pd.DataFrame) -> pd.Series:
    """apply(axis=1): still one Python call per row."""
    plan_of, rate_of = _lookups(subs, plans)

    def price(row):
        if row["status"] != "answered":
            return 0.0
        minutes = max(1, math.ceil(row["duration_s"] / 60))
        return round(minutes * rate_of[plan_of[row["caller"]]], 2)

    return calls.apply(price, axis=1).rename("cost_eur")


def rate_vector(calls: pd.DataFrame, subs: pd.DataFrame, plans: pd.DataFrame) -> pd.Series:
    """Whole-column operations: no Python loop over rows."""
    plan_of, rate_of = _lookups(subs, plans)
    rate = calls["caller"].map(plan_of).map(rate_of)
    minutes = np.maximum(1, np.ceil(calls["duration_s"] / 60))
    cost = (minutes * rate).where(calls["status"] == "answered", 0.0)
    return cost.round(2).rename("cost_eur")
