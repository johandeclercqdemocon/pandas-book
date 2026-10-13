# Appendix A. Described, not built

Everything in this book that a block of code did not measure is listed here. Each item is a statement that the book makes or leans on, and the reason that no block tests it. Read these as the documentation says, not as measured. Where an item says "checked", the book printed the evidence in the chapter that is named.

## Packages that this book does not install

The chapters mention four optional packages. [Chapter 2](../chapters/02-input-and-output.md) prints that none of them is installed.

| Package | Where it is mentioned | What the book says, from the documentation |
|---|---|---|
| `openpyxl` | Chapter 2 | pandas reads and writes `.xlsx` files with it. The book runs no Excel code. |
| `numexpr` | Chapter 18 | `query` and `eval` can use it. The book makes no claim about the gain. |
| `polars` | Chapter 19 | a tool for data that does not fit in memory. Not tested. |
| `duckdb` | Chapter 19 | the same. Not tested. |

## Behavior of other versions of pandas

The book was written on pandas 3.0.6 only. Statements about earlier versions are history, taken from the documentation and from the changes that 3.0 announced.

| Statement | Chapter |
|---|---|
| In pandas 2.x, a column of text had the dtype `object` by default. | 1, 2, 3, 4 |
| In pandas 2.x, timestamps were stored with nanosecond resolution. | 2 |
| In pandas 2.x, `.str` methods on an `object` column returned a missing value for a missing element. Chapter 3 shows this on an `object` column in 3.0, and does not run 2.x. | 3 |
| Before 3.0, a selection was sometimes a view and sometimes a copy, and `SettingWithCopyWarning` tried to tell you. | 15 |
| In 2.x, `observed` of `groupby` on categories was `False` by default. | 4 |

## Other systems

| Statement | Chapter | Why it is not measured |
|---|---|---|
| SQLite has math functions such as `CEIL` from version 3.35, and a build can be made without them. | 20 | The book prints the version that ran, 3.50.4, and the query ran. Other builds are not tested. |
| An index is a B-tree in SQLite. | 20 | The book shows the query plan before and after (`SCAN` and `SEARCH ... USING INDEX`), not the structure. |
| `ru_maxrss` of a child process includes the parent's memory at the fork. | 19 | While writing, the baseline of the first method moved between runs, and the method was changed. The mechanism is the documented behavior of Linux. |
| `VmHWM` in `/proc/self/status` is the high-water mark of the new process. | 19 | Linux only. The three baselines of the new method agreed within 1 MB. |

## What the data are

The data are synthetic and made by [`pdbook/datasets.py`](../pdbook/datasets.py). Two consequences:

- The statements about what a real network does (retries, bursts, roaming) are examples of what a real table can contain, and not findings. The data of this book have no bursts.
- A result that depends on the generator is marked as such where it appears: the loss of the cell identifier ([Chapter 5](../chapters/05-missing-data.md)) and the pass rates of the evaluation ([Chapter 23](../chapters/23-features-and-evaluation.md)).

## Time

Timings depend on the machine and on its load. The blocks that print a time have `# output varies` above the output, and an assertion that checks an order of magnitude. The chapters quote only what the assertion proves. The values printed in the book come from one run on one machine.
