"""Find out why values are missing, not only how many."""
from __future__ import annotations

import pandas as pd


def null_report(df: pd.DataFrame) -> pd.DataFrame:
    """Null count and share for each column that has at least one null."""
    n = df.isna().sum()
    n = n[n > 0]
    return pd.DataFrame({"nulls": n, "share": (n / len(df)).round(4)})


def determinants(df: pd.DataFrame, max_levels: int = 12) -> dict[str, list[str]]:
    """For each column with nulls: the low-cardinality columns that decide whether it is null.

    Column `by` decides column `col` when, in every group of `by`, the values of `col` are
    either all null or none null. Then the null is a fact about the row, not lost data.
    """
    out: dict[str, list[str]] = {}
    for col in df.columns[df.isna().any()]:
        found = []
        for by in df.columns:
            if by == col or df[by].nunique() > max_levels or df[by].isna().any():
                continue
            share = df[col].isna().groupby(df[by], observed=True).mean()
            if share.isin([0.0, 1.0]).all():
                found.append(by)
        out[col] = found
    return out
