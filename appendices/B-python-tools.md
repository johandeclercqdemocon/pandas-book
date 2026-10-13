# Appendix B. What Python already gives you

Pandas is not the only tool in this book. These pieces of the standard library did work in the chapters, and each of them is the right tool for one kind of problem.

| Need | Tool | Where it was used |
|---|---|---|
| a database with no server | `sqlite3` | [Chapter 20](../chapters/20-sql-and-pandas.md) |
| the signature of a function | `inspect.signature` | every Reference section, through `pdbook/sigs.py` |
| a time, with a monotonic clock | `time.perf_counter` | [Chapter 18](../chapters/18-performance.md) |
| a temporary file or folder | `tempfile` | [Chapters 2, 19, 20](../chapters/19-data-larger-than-memory.md) |
| a child process for a clean measure | `subprocess` | [Chapter 19](../chapters/19-data-larger-than-memory.md) |
| a warning that you want to see, not print | `warnings.catch_warnings(record=True)` | [Chapters 2, 3, 15](../chapters/15-copy-on-write-and-traps.md) |
| JSON, one object for each line | `json.loads` | [Chapter 22](../chapters/22-json-and-nested-records.md) |
| a record type with named fields | `dataclasses` | [Chapters 15, 17](../chapters/17-data-validation.md) |
| checking that a package is installed | `importlib.util.find_spec` | [Chapter 2](../chapters/02-input-and-output.md) |

A rule for choosing: when the question is about tables of data, use pandas. When the question is about the program (a process, a file, a clock, a warning), use the standard library. Its tools are older and smaller.
