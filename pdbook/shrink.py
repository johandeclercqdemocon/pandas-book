"""Make a DataFrame smaller without changing what it says."""
from __future__ import annotations

import pandas as pd


def _is_text(s: pd.Series) -> bool:
    return isinstance(s.dtype, pd.StringDtype) or s.dtype == object


def shrink(df: pd.DataFrame, max_unique_share: float = 0.5, float_to_int: bool = False) -> pd.DataFrame:
    """Return a copy with smaller dtypes.

    text with few distinct values -> category
    integers                      -> the smallest integer type that holds every value
    floats of whole numbers       -> nullable Int (only when float_to_int is True)

    Floats are never narrowed to float32: that changes values.
    """
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if _is_text(s):
            if len(s) and s.nunique() / len(s) <= max_unique_share:
                out[col] = s.astype("category")
        elif pd.api.types.is_bool_dtype(s):
            continue
        elif pd.api.types.is_integer_dtype(s) and not isinstance(s.dtype, pd.api.extensions.ExtensionDtype):
            out[col] = pd.to_numeric(s, downcast="integer")
        elif float_to_int and pd.api.types.is_float_dtype(s):
            whole = s.dropna()
            if len(whole) and (whole == whole.round()).all():
                small = pd.to_numeric(whole.astype("int64"), downcast="integer").dtype
                out[col] = s.astype(str(small).capitalize())
    return out


def memory_report(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    """Deep memory in bytes for each column, before and after, and the dtype change."""
    b = before.memory_usage(deep=True).drop("Index")
    a = after.memory_usage(deep=True).drop("Index")
    return pd.DataFrame({
        "before": before.dtypes.astype(str), "after": after.dtypes.astype(str),
        "bytes_before": b, "bytes_after": a,
    })


def same_content(before: pd.DataFrame, after: pd.DataFrame) -> bool:
    """True when `after`, cast back to the dtypes of `before`, equals `before`."""
    try:
        pd.testing.assert_frame_equal(after.astype(before.dtypes.to_dict()), before)
    except AssertionError:
        return False
    return True
