"""Chapter 5: why is each value missing?"""
from pdbook.io import load_calls
from pdbook.nulls import determinants, null_report

calls = load_calls()
print(null_report(calls))
print()
for col, by in determinants(calls).items():
    print(f"{col:10s} is null because of: {', '.join(by) if by else 'nothing in this table (lost data)'}")
