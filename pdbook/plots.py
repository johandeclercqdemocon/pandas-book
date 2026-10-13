"""Four plots of the call data. Each function draws on an Axes and returns it.

The backend is Agg, so the code runs on a machine with no display. A plot is tested by the data
that it holds, not by its pixels.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def plot_hourly_calls(calls: pd.DataFrame, tz: str = "Europe/Brussels", ax=None):
    """Bar chart: calls started in each hour of the day, in time zone `tz`."""
    hours = calls["start"].dt.tz_convert(tz).dt.hour
    counts = hours.value_counts().reindex(range(24), fill_value=0).sort_index()
    ax = ax or plt.subplots(figsize=(7, 3.2))[1]
    counts.plot.bar(ax=ax, color="#3b6ea5", width=0.85)
    ax.set_xlabel(f"hour of the day ({tz})")
    ax.set_ylabel("calls in September")
    ax.set_title("Calls by hour of the day")
    return ax


def plot_traffic_grid(grid: pd.DataFrame, ax=None):
    """Heat map of the 7 x 24 traffic grid from Chapter 10."""
    ax = ax or plt.subplots(figsize=(7.5, 3.4))[1]
    image = ax.imshow(grid.to_numpy(), aspect="auto", cmap="viridis")
    ax.set_xticks(range(0, 24, 3), labels=[str(h) for h in range(0, 24, 3)])
    ax.set_yticks(range(len(grid)), labels=grid.index.tolist())
    ax.set_xlabel("hour of the day (Europe/Brussels)")
    ax.set_title("Calls for each weekday and hour")
    ax.figure.colorbar(image, ax=ax, label="calls")
    return ax


def plot_kpi_spike(kpi: pd.DataFrame, flags: pd.Series, cell: str = "BRU-002", ax=None):
    """Drop rate of one cell as a line, with the flagged samples marked."""
    one = kpi[kpi["cell_id"] == cell].sort_values("ts")
    ax = ax or plt.subplots(figsize=(7, 3.2))[1]
    ax.plot(one["ts"], one["drop_rate_pct"], color="#3b6ea5", linewidth=1, label="drop rate")
    hit = one[flags.loc[one.index]]
    ax.scatter(hit["ts"], hit["drop_rate_pct"], color="#c0392b", zorder=3, s=18, label="flagged")
    ax.set_ylabel("drop rate (%)")
    ax.set_title(f"Cell {cell}: drop rate, 5-minute samples")
    ax.legend(loc="upper left")
    ax.figure.autofmt_xdate()
    return ax


def plot_duration_hist(calls: pd.DataFrame, ax=None):
    """Histogram of answered-call durations on a log axis, with the median marked."""
    d = calls.loc[(calls["status"] == "answered") & (calls["duration_s"] > 0), "duration_s"]
    bins = np.logspace(0, np.log10(d.max()), 40)
    ax = ax or plt.subplots(figsize=(7, 3.2))[1]
    ax.hist(d, bins=bins, color="#3b6ea5")
    ax.set_xscale("log")
    ax.axvline(d.median(), color="#c0392b", linestyle="--", label=f"median {d.median():.0f} s")
    ax.set_xlabel("duration (s, log scale)")
    ax.set_ylabel("answered calls")
    ax.set_title("Duration of answered calls")
    ax.legend()
    return ax
