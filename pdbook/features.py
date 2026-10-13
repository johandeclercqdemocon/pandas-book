"""Features for one question: how many calls will a subscriber make after the cutoff?

A feature may use only calls that start before the cutoff. `assert_no_leak` proves it by
changing the calls after the cutoff and checking that the features do not move.
"""
from __future__ import annotations

import pandas as pd

TZ = "Europe/Brussels"


def _split(calls: pd.DataFrame, cutoff: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    limit = pd.Timestamp(cutoff, tz=TZ)
    before = calls[calls["start"] < limit]
    after = calls[calls["start"] >= limit]
    return before, after, limit


def past_features(calls: pd.DataFrame, subscribers: pd.Series, cutoff: str) -> pd.DataFrame:
    """One row for each subscriber id in `subscribers`, from the calls before `cutoff` only."""
    before, _, limit = _split(calls, cutoff)
    g = before.assign(answered=before["status"].eq("answered"),
                      talk_min=before["duration_s"].fillna(0) / 60,
                      day=before["start"].dt.tz_convert(TZ).dt.normalize()).groupby("caller")
    out = pd.DataFrame({
        "calls": g.size(),
        "answered_share": g["answered"].mean(),
        "talk_min": g["talk_min"].sum(),
        "active_days": g["day"].nunique(),
        "days_since_last": (limit - g["start"].max()).dt.total_seconds() / 86400,
    }).reindex(pd.Index(subscribers, name="caller"))
    out[["calls", "talk_min", "active_days"]] = out[["calls", "talk_min", "active_days"]].fillna(0)
    return out


def target(calls: pd.DataFrame, subscribers: pd.Series, cutoff: str) -> pd.Series:
    """Calls that each subscriber made at or after `cutoff`."""
    _, after, _ = _split(calls, cutoff)
    return after.groupby("caller").size().reindex(pd.Index(subscribers, name="caller"), fill_value=0).rename("future_calls")


def leaky_features(calls: pd.DataFrame, subscribers: pd.Series) -> pd.DataFrame:
    """The same idea, written the easy way: group over the whole month. It leaks the target."""
    g = calls.groupby("caller")
    return pd.DataFrame({"calls": g.size()}).reindex(pd.Index(subscribers, name="caller"), fill_value=0)


def assert_no_leak(feature_fn, calls: pd.DataFrame, subscribers: pd.Series, cutoff: str) -> None:
    """Raise AssertionError if `feature_fn(calls, subscribers)` changes when only the future changes.

    The future is the calls at or after `cutoff`. Two changes are tried, and both must leave the
    features as they were:

    1. the future is removed;
    2. every future call is given to one subscriber, with a duration of 1 second.

    Shuffling the callers of the future is not enough: a count for each caller does not move.
    """
    before, after, _ = _split(calls, cutoff)
    one_caller = after.assign(caller=str(subscribers.iloc[0]), duration_s=1.0, status="answered")
    expected = feature_fn(calls, subscribers).reset_index(drop=True)
    for name, changed in [("future removed", before), ("future given to one caller", pd.concat([before, one_caller]))]:
        got = feature_fn(changed, subscribers).reset_index(drop=True)
        try:
            pd.testing.assert_frame_equal(expected, got)
        except AssertionError as error:
            raise AssertionError(f"features change when the future changes ({name})") from error
