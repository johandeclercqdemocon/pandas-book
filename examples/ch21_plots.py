"""Chapter 21: draw four figures into figures/ and test each one by the data that it holds."""
import pathlib

import matplotlib.pyplot as plt
import numpy as np

from pdbook.io import load_calls, load_kpi
from pdbook.plots import plot_duration_hist, plot_hourly_calls, plot_kpi_spike, plot_traffic_grid
from pdbook.spikes import flag_spikes
from pdbook.traffic import traffic_grid

OUT = pathlib.Path(__file__).resolve().parent.parent / "figures"
OUT.mkdir(exist_ok=True)
calls = load_calls()
kpi = load_kpi().drop_duplicates(["ts", "cell_id"]).reset_index(drop=True)
grid = traffic_grid(calls)
flags = flag_spikes(kpi, z=4)

figures = {
    "hourly": plot_hourly_calls(calls),
    "grid": plot_traffic_grid(grid),
    "spike": plot_kpi_spike(kpi, flags),
    "hist": plot_duration_hist(calls),
}
heights = [p.get_height() for p in figures["hourly"].patches]
assert int(sum(heights)) == len(calls) and len(heights) == 24
assert np.array_equal(figures["grid"].images[0].get_array(), grid.to_numpy())
assert len(figures["spike"].collections[0].get_offsets()) == 7
assert int(sum(p.get_height() for p in figures["hist"].patches)) == int((calls["status"] == "answered").sum())

for name, ax in figures.items():
    ax.figure.tight_layout()
    ax.figure.savefig(OUT / f"{name}.png", dpi=110)
    plt.close(ax.figure)
    print(f"{name:7s} {(OUT / f'{name}.png').stat().st_size:>7,d} bytes  title: {ax.get_title()}")
