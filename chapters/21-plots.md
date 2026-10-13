# 21. Plots

> **Build** — `pdbook/plots.py`: four plots of the call data (calls by hour, a traffic heat map, a KPI series with flagged samples, a duration histogram), each tested by the data that it holds, and each saved as a file in `figures/`.
>
> **Theory kept** — `DataFrame.plot` and `Series.plot` call matplotlib. A plot is a function of a table: shape the table first, then plot. Give each plot a title, axis labels with units and the zone of time. Test a plot with the numbers that are in it, and look at it once.
>
> **Source** — New. Library: [`pdbook/plots.py`](../pdbook/plots.py). Matplotlib is the one extra package that this book installs.
>
> **Run this first** — `uv run python -m examples.ch21_plots`, which is [`examples/ch21_plots.py`](../examples/ch21_plots.py). It writes four files to [`figures/`](../figures/). Exercises: [`exercises/21.md`](../exercises/21.md). Solutions: [`exercises/solutions/21.md`](../exercises/solutions/21.md).

## Shape the table, then plot

pandas plots a Series or a DataFrame with `.plot`, and a method for each kind: `.plot.bar()`, `.plot.line()`, `.plot.hist()`, `.plot.scatter()`. The index becomes the x axis and each column becomes a series. This means that most of the work is in the table (Chapters 8 to 10), and the plot is one line.

```python
import matplotlib

matplotlib.use("Agg")

from pdbook.io import load_calls

calls = load_calls()
hours = calls["start"].dt.tz_convert("Europe/Brussels").dt.hour
per_hour = hours.value_counts().reindex(range(24), fill_value=0).sort_index()
ax = per_hour.plot.bar()

print(type(ax).__name__, len(ax.patches))
print([int(p.get_height()) for p in ax.patches][:6])
print(per_hour.iloc[:6].tolist())
```

```text
Axes 24
[98, 102, 94, 101, 109, 199]
[98, 102, 94, 101, 109, 199]
```

`plot.bar` returns a matplotlib `Axes`. The 24 bars are `patches`, and their heights are the numbers of the Series. Two things in the code come from earlier chapters: the conversion to local time ([Chapter 12](12-dates-and-resampling.md)), and `reindex` so that an hour without calls is a bar of height 0 ([Chapter 11](11-index-and-multiindex.md)).

Choose `matplotlib.use("Agg")` on a server, in a job, or in a test. It draws to a file and needs no display.

## A plot has to say what it shows

A plot without a unit or a zone is a guess. The module [`pdbook/plots.py`](../pdbook/plots.py) puts four things on every figure. It gives a title that names the content and axis labels with units. It puts the time zone in the label of a time axis. It adds a legend when there is more than one mark. This is the first figure, which the example module writes to `figures/hourly.png`:

![Calls by hour of the day](../figures/hourly.png)

The figure has about 100 calls an hour from 00:00 to 05:00. It rises from 06:00, and it peaks at 09:00, 15:00 and 19:00. There is a dip to about 1,000 calls at 12:00. The busiest hour is 15:00 local time, the same hour that [Chapter 10](10-pivot-and-melt.md) found in the table. A figure that disagrees with a table that you trust is a bug in one of them.

## Heat map of a grid

A table of counts with two dimensions is a heat map. `imshow` draws the array, and the tick labels come from the index and the columns:

![Calls for each weekday and hour](../figures/grid.png)

From 07:00 to 21:00 the Saturday and Sunday rows are darker than the weekday rows. The Tuesday row has the brightest cell at 09:00, the 300 calls of Chapter 10. Wednesday at 19:00 is the second brightest. All cells use one colour scale, so you can compare rows by colour.

## Mark the events that a rule found

A line of a KPI is easy to read, and a short event is easy to miss in a month of data. Draw the flagged samples on top of the line, so that the figure shows what the detector of [Chapter 13](13-windows-shifts-gaps.md) found:

![Drop rate of BRU-002 with seven flagged samples](../figures/spike.png)

The spike of 25 October is 7 samples at about 10% against a normal level of about 0.6%. The marks sit on the spike, and none is on the rest of the line.

## Distributions on a log axis

Call durations have a long tail: the median is 79 seconds and the longest call is 3,836 seconds. On a linear axis the bars of the long calls are not visible. A log axis with log-spaced bins shows the whole range. On this axis the shape is close to a bell, with the median of 79 seconds at its top:

![Duration of answered calls](../figures/hist.png)

## Test a plot by its data

A pixel comparison breaks with every version of matplotlib. Test the numbers that are in the figure. The Axes holds them:

```python
import matplotlib

matplotlib.use("Agg")

import numpy as np

from pdbook.io import load_calls, load_kpi
from pdbook.plots import plot_duration_hist, plot_hourly_calls, plot_kpi_spike, plot_traffic_grid
from pdbook.spikes import flag_spikes
from pdbook.traffic import traffic_grid

calls = load_calls()
kpi = load_kpi().drop_duplicates(["ts", "cell_id"]).reset_index(drop=True)
grid = traffic_grid(calls)

hourly = plot_hourly_calls(calls)
print(len(hourly.patches), int(sum(p.get_height() for p in hourly.patches)) == len(calls))

heat = plot_traffic_grid(grid)
print(bool(np.array_equal(heat.images[0].get_array(), grid.to_numpy())))

spike = plot_kpi_spike(kpi, flag_spikes(kpi, z=4))
print(len(spike.collections[0].get_offsets()), spike.get_title())

hist = plot_duration_hist(calls)
print(int(sum(p.get_height() for p in hist.patches)), hist.get_xscale())
```

```text
24 True
True
7 Cell BRU-002: drop rate, 5-minute samples
15526 log
```

The four tests are four lines. There are 24 bars, and they add up to 20,000 calls. The image holds the grid, cell by cell. The scatter has 7 points. The histogram holds the 15,526 answered calls, and its axis is logarithmic. These are the properties that a change in the table code breaks.

A test of the numbers does not say that the figure is readable. Open the file once, and look. A label that covers a tick, or a colour that a colour-blind person cannot read, is not in the data.

## How it works

A figure is a tree of objects. A `Figure` holds one or more `Axes`. An `Axes` holds the marks as objects: a bar chart has one `Rectangle` in `patches` for each bar, a line plot has `Line2D` objects, a scatter has a collection.

`Series.plot.bar` is a short way to build this tree from a Series: it puts the index labels on the tick marks and puts the bars at the positions 0, 1, 2 and so on. The picture is made only when you save the figure, and you can read the tree before that.

```python
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from pdbook.io import load_calls
from pdbook.plots import plot_hourly_calls

calls = load_calls()
ax = plot_hourly_calls(calls)
fig = ax.figure
centers = [float(p.get_x() + p.get_width() / 2) for p in ax.patches]

print(type(fig).__name__, len(fig.axes), type(ax).__name__, len(ax.patches))
print(type(ax.patches[0]).__name__, centers[:3], centers[-1])
print([t.get_text() for t in ax.get_xticklabels()][:3], ax.get_xlabel())
plt.close(fig)
```

```text
Figure 1 Axes 24
Rectangle [0.0, 1.0, 2.0] 23.0
['0', '1', '2'] hour of the day (Europe/Brussels)
```

The figure has one `Axes`, and the `Axes` has 24 `Rectangle` objects, one for each hour. The bar centers are the positions 0, 1, 2 and up to 23, and the tick labels are the hours as text. A test that reads `patches` reads the numbers that the bars were made from, and it needs no image.

- **Invariant.** What is drawn is in the objects of the tree, and the objects hold the numbers.
- **Failure.** A label is a string with no link to the data, so it can be wrong while the figure is complete ([the exercise on a figure that lies](../exercises/solutions/21.md)).
- **Cost.** The tree is cheap. The cost is in the rendering when you save, and it grows with the number of marks.

## Reference

```python
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from pdbook.plots import plot_duration_hist, plot_hourly_calls, plot_kpi_spike, plot_traffic_grid
from pdbook.sigs import show_signature

show_signature(pd.Series.plot.bar)
show_signature(plt.subplots, ["nrows", "ncols", "fig_kw"])
show_signature(plt.Figure.savefig, ["fname", "kwargs"])
show_signature(plot_hourly_calls)
show_signature(plot_traffic_grid)
show_signature(plot_kpi_spike)
show_signature(plot_duration_hist)
```

```text
PlotAccessor.bar(
    self
    x: 'Hashable | None' = None
    y: 'Hashable | None' = None
    color: 'str | Sequence[str] | dict | None' = None
    **kwargs
)
subplots(
    nrows: 'int' = 1
    ncols: 'int' = 1
    **fig_kw: 'Any'
)  # 7 more parameters
Figure.savefig(
    fname
    **kwargs
)  # 2 more parameters
plot_hourly_calls(
    calls: 'pd.DataFrame'
    tz: 'str' = 'Europe/Brussels'
    ax=None
)
plot_traffic_grid(
    grid: 'pd.DataFrame'
    ax=None
)
plot_kpi_spike(
    kpi: 'pd.DataFrame'
    flags: 'pd.Series'
    cell: 'str' = 'BRU-002'
    ax=None
)
plot_duration_hist(
    calls: 'pd.DataFrame'
    ax=None
)
```

| Parameter | Default | What it does here | What goes wrong |
|---|---|---|---|
| `Series.plot.bar(color=..., **kwargs)` | `None` | a bar chart; keywords go to matplotlib (`ax`, `width`, `title`, ...) | — |
| `plt.subplots(nrows, ncols, **fig_kw)` | `1`, `1` | a figure and its axes; `figsize` is a keyword of `fig_kw` | — |
| `Figure.savefig(fname, **kwargs)` | required | write the figure; `dpi` is a keyword | — |
| `plot_hourly_calls(calls, tz=..., ax=...)` | required, `'Europe/Brussels'`, `None` | bars for each hour of the day in zone `tz` | the label and the conversion use the same `tz`, so they cannot disagree |
| `plot_traffic_grid(grid, ax=...)` | required, `None` | heat map of the 7 by 24 grid | — |
| `plot_kpi_spike(kpi, flags, cell=..., ax=...)` | required, required, `'BRU-002'`, `None` | the line of one cell and the flagged samples | — |
| `plot_duration_hist(calls, ax=...)` | required, `None` | log-scale histogram of answered durations | — |

Each `plot_` function returns the `Axes`, so that a test can read its `patches`, `images` and `collections`.

## What you have now

- You shape the table first and plot with `.plot`, and you set `Agg` for jobs.
- You put a title, units, a zone and a legend on each figure.
- You draw the events that a rule found on top of the series.
- You test a figure by the numbers in its Axes, and you look at it once.

The next chapter reads data that is not a table: nested JSON.

Next: [Chapter 22, JSON and nested records](22-json-and-nested-records.md).
