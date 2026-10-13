"""Join the call records with the lookup tables, and refuse to multiply rows."""
from __future__ import annotations

import pandas as pd


def _lookup(calls: pd.DataFrame, table: pd.DataFrame, left_on: str, right_on: str, name: str):
    """Left join, many-to-one. Raises MergeError if the right key is not unique."""
    out = calls.merge(table, how="left", left_on=left_on, right_on=right_on,
                      validate="m:1", indicator=True)
    if len(out) != len(calls):                      # cannot happen after validate, kept as a guard
        raise ValueError(f"{name}: {len(calls)} rows became {len(out)}")
    unmatched = int(((out["_merge"] == "left_only") & out[left_on].notna()).sum())
    return out.drop(columns="_merge"), unmatched


def enrich(calls: pd.DataFrame, subs: pd.DataFrame, cells: pd.DataFrame,
           plans: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Add plan, home city, cell city and technology, price per minute and on-net flag.

    Returns the enriched table and, for each lookup, the number of rows whose key was
    present but not found. A missing key (NaN) is not counted: it is missing, not unmatched.
    """
    report: dict[str, int] = {}
    out = calls
    out, report["caller -> subscribers"] = _lookup(
        out, subs[["subscriber_id", "plan", "city"]].rename(columns={"city": "home_city"}),
        "caller", "subscriber_id", "subscribers")
    out = out.drop(columns="subscriber_id")
    out, report["cell_id -> cells"] = _lookup(
        out, cells[["cell_id", "city", "tech"]].rename(columns={"city": "cell_city", "cell_id": "cell_key"}),
        "cell_id", "cell_key", "cells")
    out = out.drop(columns="cell_key")
    out, report["plan -> plans"] = _lookup(
        out, plans[["plan", "rate_per_min_eur"]], "plan", "plan", "plans")
    on_net = subs[["msisdn", "subscriber_id"]].rename(columns={"subscriber_id": "callee_subscriber"})
    out, _ = _lookup(out, on_net, "callee", "msisdn", "callee")
    out = out.drop(columns="msisdn")
    out["on_net"] = out["callee_subscriber"].notna()
    return out, report
