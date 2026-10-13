"""Ten ways that pandas gives a wrong answer without an error.

Each trap is a pair of functions on small data: `naive` is what people write, `correct` is what
they meant. A trap is "live" when the two give different results. The test in Chapter 15 checks
that all ten are live in the installed version of pandas.
"""
from __future__ import annotations

import io
import warnings
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Trap:
    name: str
    chapter: int
    naive: Callable[[], Any]
    correct: Callable[[], Any]


def _alignment_naive():
    a = pd.Series([1, 2, 3], index=["a", "b", "c"])
    b = pd.Series([1, 2, 3], index=["c", "b", "a"])
    return (a + b).tolist()                      # matched by label: [4, 4, 4]


def _alignment_correct():
    a = pd.Series([1, 2, 3], index=["a", "b", "c"])
    b = pd.Series([1, 2, 3], index=["c", "b", "a"])
    return (a.to_numpy() + b.to_numpy()).tolist()  # what a person who looks at two lists expects


def _phone_naive():
    return pd.read_csv(io.StringIO("phone\n0477123456\n"))["phone"].tolist()


def _phone_correct():
    return pd.read_csv(io.StringIO("phone\n0477123456\n"), dtype={"phone": "str"})["phone"].tolist()


def _groupby_naive():
    df = pd.DataFrame({"k": ["a", None, "a"], "v": [1, 2, 3]})
    return int(df.groupby("k")["v"].sum().sum())


def _groupby_correct():
    df = pd.DataFrame({"k": ["a", None, "a"], "v": [1, 2, 3]})
    return int(df.groupby("k", dropna=False)["v"].sum().sum())


def _mask_naive():
    d = pd.Series([1.0, np.nan, 3.0])
    return int((d > 0).sum() + (d <= 0).sum())      # 2, not 3: the null is in neither


def _mask_correct():
    d = pd.Series([1.0, np.nan, 3.0])
    return int((d > 0).sum() + (d <= 0).sum() + d.isna().sum())


def _chained_naive():
    df = pd.DataFrame({"x": [1, 2, 3]})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df[df["x"] > 1]["x"] = 0
    return df["x"].tolist()


def _chained_correct():
    df = pd.DataFrame({"x": [1, 2, 3]})
    df.loc[df["x"] > 1, "x"] = 0
    return df["x"].tolist()


def _slice_naive():
    d = pd.DataFrame({"v": [10, 20, 30, 40]}, index=["a", "b", "c", "d"])
    return d.loc["a":"c"]["v"].tolist()            # a person who means "before c" gets three rows


def _slice_correct():
    d = pd.DataFrame({"v": [10, 20, 30, 40]}, index=["a", "b", "c", "d"])
    return d.iloc[0:2]["v"].tolist()               # the two rows before "c": the position slice stops before the end


def _dup_lookup_naive():
    calls = pd.DataFrame({"caller": ["A", "B"], "sec": [60, 30]})
    subs = pd.DataFrame({"id": ["A", "A", "B"], "plan": ["x", "x", "y"]})
    return int(calls.merge(subs, left_on="caller", right_on="id")["sec"].sum())


def _dup_lookup_correct():
    calls = pd.DataFrame({"caller": ["A", "B"], "sec": [60, 30]})
    subs = pd.DataFrame({"id": ["A", "A", "B"], "plan": ["x", "x", "y"]}).drop_duplicates("id")
    return int(calls.merge(subs, left_on="caller", right_on="id", validate="m:1")["sec"].sum())


def _int8_naive():
    return pd.Series([100, 100], dtype="int8").add(pd.Series([100, 100], dtype="int8")).tolist()


def _int8_correct():
    return pd.Series([100, 100], dtype="int64").add(pd.Series([100, 100], dtype="int64")).tolist()


def _float_naive():
    return bool((pd.Series([0.1]) + pd.Series([0.2])).eq(0.3).iloc[0])


def _float_correct():
    return bool(np.isclose(pd.Series([0.1]) + pd.Series([0.2]), 0.3).all())


def _mean_naive():
    return float(pd.Series([1, 2, None, 6]).mean())          # 3.0: the null is skipped


def _mean_correct():
    return float(pd.Series([1, 2, None, 6]).fillna(0).mean())  # 2.25: a null counts as zero


TRAPS = [
    Trap("a Series adds by label, not by position", 1, _alignment_naive, _alignment_correct),
    Trap("read_csv turns a phone number into an integer", 2, _phone_naive, _phone_correct),
    Trap("groupby drops rows with a missing key", 5, _groupby_naive, _groupby_correct),
    Trap("a condition and its opposite miss the nulls", 3, _mask_naive, _mask_correct),
    Trap("chained assignment changes nothing", 3, _chained_naive, _chained_correct),
    Trap("a label slice includes its end", 3, _slice_naive, _slice_correct),
    Trap("a duplicate in a lookup table multiplies rows", 9, _dup_lookup_naive, _dup_lookup_correct),
    Trap("a small integer type wraps around", 4, _int8_naive, _int8_correct),
    Trap("0.1 + 0.2 is not 0.3", 15, _float_naive, _float_correct),
    Trap("mean skips nulls", 5, _mean_naive, _mean_correct),
]


def live(trap: Trap) -> bool:
    """True when the naive code and the intended code give different results."""
    return trap.naive() != trap.correct()
