"""A first look at a DataFrame: what is in it, how big, what is missing."""
from __future__ import annotations

import pandas as pd


def first_look(df: pd.DataFrame) -> pd.DataFrame:
    """One row per column: dtype, null count, distinct count, first value."""
    return pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "nulls": df.isna().sum(),
        "unique": df.nunique(),
        "first": df.iloc[0].astype(str),
    })


def headline(df: pd.DataFrame) -> str:
    """One line: rows, columns and deep memory."""
    mb = df.memory_usage(deep=True).sum() / 1e6
    return f"{len(df):,} rows x {df.shape[1]} columns, {mb:.1f} MB"
