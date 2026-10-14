# Appendix C. What went wrong

This list is the record of statements that the book made, and that a run or an audit then showed to be wrong. They are fixed in the text. They are listed here because the same habits come back. The second table lists statements of the pandas documentation, or of common advice, that the installed pandas 3.0.6 does not follow.

## Wrong in this book

| Chapter | The wrong statement | What the run or the audit showed | How it was caught |
|---|---|---|---|
| all | each function has its signature and its parameters explained | the signatures printed only the parameters that the chapter used, and hid 482 others behind `# N more parameters`. 59 of the printed parameters had no row in their table. No check tied a table to its signature | a reader found two missing rows in a sister book. Every callable now has a `####` block with its full signature and one row for each parameter, and the checker fails when a row is missing or a default is wrong |
| [6](../chapters/06-text-and-date-cleanup.md) | `to_datetime(format="mixed", dayfirst=True)` parses the four date formats of the export | it also swaps day and month in ISO dates: 30 of the 78 ISO dates were wrong, for example `2024-11-04` became 11 April. No warning. `clean_contacts` used it | a run that compared the mixed parser with one exact format for each pattern. The new function `dates` reads each format with its exact pattern |
| [2](../chapters/02-input-and-output.md) | in a draft row, `dayfirst=False` swaps day and month for every day up to 12 | a column with `01/02/2026` and then `13/02/2026` stays `str`, with no warning | running the case before the row went in |
| [2](../chapters/02-input-and-output.md) | in a draft row, `to_csv(decimal=",")` with `sep=","` gives a file that no reader can split | pandas quotes each number, as `"1,5"`. A reader with the default `decimal` reads text | the same |
| [13](../chapters/13-windows-shifts-gaps.md) | in a draft row, `flag_spikes(window="1h")` finds nothing because a short window learns the spike | a window of one hour holds at most 12 samples, fewer than `min_periods=50`, so no sample gets a score. With `min_periods=6` it flags samples | a second run with a smaller `min_periods` |
| [3](../chapters/03-selection.md) | the late records are "from Chapter 3", in Chapter 3 | the 1,000 late records come from the data generator, and [Chapter 12](../chapters/12-dates-and-resampling.md) uses them | reading the chapter while its blocks were written |
| [3](../chapters/03-selection.md) | the Reference listed `nlargest`, and a row said that `loc[4:10]` on an unsorted index returns 6 rows | the chapter never used `nlargest`, and no block anywhere printed the 6 rows | the audit of each row against a block. `nlargest` now has its block and an example in [Chapter 14](../chapters/14-ranks-running-totals-sessions.md) |
| [4](../chapters/04-types-and-memory.md) | `int16` has the range ±32,767 | -32,768 to 32,767, as the block prints | the same audit |
| [9](../chapters/09-joins.md) | an inner join loses 144 calls when 5 subscribers are not in the lookup | no block made or printed this case | the same audit. The row now has the measured join with the cell table: 19,723 of 20,000 |
| [14](../chapters/14-ranks-running-totals-sessions.md) | "how many are strictly higher" is the rank `min` | for an ascending rank, `min` is one more than the number of values strictly lower | checking the sentence against the printed ranks 1, 2, 2, 4 |
| [17](../chapters/17-data-validation.md) | `plant_faults` makes six kinds of fault | it makes seven: a repeated id, a negative duration, a missing duration, an unknown caller, a bad callee, a start outside the month and a codec on a call that was not answered | counting the assignments in the code |
| [18](../chapters/18-performance.md) | Chapter 7 shows a larger ratio at 20,000 rows than at 2,000 rows | Chapter 7 has no timing at 2,000 rows | the same audit. [Chapter 18](../chapters/18-performance.md) now measures it: 2 times at 200 rows, 14 at 2,000 and 64 at 20,000 in the last run. The assertion proves only that the ratio grows by more than three times |
| [7](../chapters/07-new-columns.md) | the `precision` row of `pd.cut`: the interval named `(0.1, 1.1]` has the edges 0.1216 and 1.0556 | the row did not say which data gave these edges, so no reader could repeat it. With `bins=[0.1216, 1.0556]` and `precision=1`, the `Interval` itself has the edges 0.1 and 1.1, and 1.08 still becomes `NaN` | a second pass that ran each number of the new rows again |
| [23](../chapters/23-features-and-evaluation.md) | the `n_boot` row: with 50 resamples, the lower end moved from 0.012 to 0.020 between seeds | over the seeds 0 to 5 it went from 0.006 to 0.020. The row showed two seeds of six | the same pass |
| [21](../chapters/21-plots.md) | the busiest hour, 15:00, is the hour that Chapter 10 found | Chapter 10 found Tuesday at 09:00 as the busiest cell, and it never ranked the hours. 15:00 has 1,441 calls, 9 more than 09:00 | counting the hours with `value_counts` |

## What the documentation or common advice says, and pandas 3.0.6 does not do

| Chapter | The statement | What the run showed |
|---|---|---|
| [1](../chapters/01-series-and-dataframe.md) | the docstring of `DataFrame`: with `copy=None`, a 2-D NumPy array is not copied | it is copied. `np.shares_memory` is `False` with the default and `True` with `copy=False` |
| [2](../chapters/02-input-and-output.md) | `low_memory=True` can give one column with values of two types, and a `DtypeWarning` | 300,000 integers and then one text value give one `str` column, with no warning. One float or one gap gives `float64` |
| [17](../chapters/17-data-validation.md) | the tolerance of `assert_frame_equal` is the one of `np.isclose` | pandas uses the rule of `math.isclose`, which is symmetric. On `1 + 1.0005e-5` against `1.0`, NumPy says equal and pandas says different |

## Checks that found nothing

Four checks found no error at the last run: the link check, the contract check, the output check and the check that every `pd.*` name in the text exists.
