"""Chapter 4: shrink the call records and prove that nothing changed."""
from pdbook.io import load_calls
from pdbook.shrink import memory_report, same_content, shrink

calls = load_calls()
small = shrink(calls, float_to_int=True)
rep = memory_report(calls, small)
print(rep.to_string())
total_before, total_after = rep["bytes_before"].sum(), rep["bytes_after"].sum()
print(f"\ntotal {total_before:,d} -> {total_after:,d} bytes ({total_after / total_before:.0%})")
print("same content:", same_content(calls, small))
