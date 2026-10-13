"""Chapter 23: features from the past only, a test for leakage, and a paired comparison of two configs."""
import numpy as np
import pandas as pd

from pdbook.evals import compare_configs, load_runs
from pdbook.features import assert_no_leak, leaky_features, past_features, target
from pdbook.io import load_calls, load_subscribers

calls, subs = load_calls(), load_subscribers()["subscriber_id"]
cutoff = "2026-09-22"
X, y, L = past_features(calls, subs, cutoff), target(calls, subs, cutoff), leaky_features(calls, subs)


def score(x: pd.Series) -> tuple[float, float]:
    prediction = x * (y.sum() / x.sum())
    return float(np.corrcoef(x, y)[0, 1]), float((prediction - y).abs().mean())


print("past features :  corr %.3f  MAE %.2f" % score(X["calls"]))
print("leaky feature :  corr %.3f  MAE %.2f" % score(L["calls"]))
assert_no_leak(lambda c, s: past_features(c, s, cutoff), calls, subs, cutoff)
print("past_features passes the leak test")
try:
    assert_no_leak(leaky_features, calls, subs, cutoff)
except AssertionError as error:
    print("leaky_features fails:", error)

result = compare_configs(load_runs())
print({k: round(v, 4) for k, v in result.items()})
