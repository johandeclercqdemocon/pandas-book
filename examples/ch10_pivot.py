"""Chapter 10: the traffic grid, its long form, and the round trip."""
import pandas as pd

from pdbook.io import load_calls
from pdbook.traffic import to_long, to_wide, traffic_grid

calls = load_calls()
grid = traffic_grid(calls)
long = to_long(grid)
print(grid.loc[:, 7:20].to_string())
print()
print("grid total  :", int(grid.to_numpy().sum()), "of", len(calls))
print("long shape  :", long.shape)
busiest = long.sort_values("calls", ascending=False).iloc[0]
print("busiest cell:", busiest["weekday"], f"{int(busiest['hour']):02d}:00", int(busiest["calls"]), "calls")
pd.testing.assert_frame_equal(to_wide(long), grid)
print("round trip  : equal")
