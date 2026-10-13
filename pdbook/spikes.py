"""Flag a measurement that is far above what the same cell did in the last day."""
from __future__ import annotations

import pandas as pd


def flag_spikes(kpi: pd.DataFrame, column: str = "drop_rate_pct", window: str = "1D",
                z: float = 4.0, min_periods: int = 50) -> pd.Series:
    """True where `column` is more than `z` standard deviations above its trailing mean.

    The baseline of each sample is the mean and standard deviation of the same cell in the
    `window` before it, not including the sample itself (closed="left"). A row with fewer than
    `min_periods` samples in its window is never flagged: there is no baseline yet.
    The input must be unique on (ts, cell_id). The result has the index of `kpi`.
    """
    flags = pd.Series(False, index=kpi.index)
    for _, g in kpi.sort_values("ts").groupby("cell_id"):
        s = g.set_index("ts")[column]
        roll = s.rolling(window, min_periods=min_periods, closed="left")
        score = (s - roll.mean()) / roll.std()
        flags.loc[g.index] = (score > z).to_numpy()
    return flags
