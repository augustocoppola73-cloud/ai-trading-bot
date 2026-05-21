# Debugging Workflow

When debugging:

1. Reproduce the issue or identify the failing input.
2. Locate the module boundary where behavior diverges.
3. Inspect DataFrame columns and row counts at each stage.
4. Check generated CSV artifacts when dashboard behavior is involved.
5. Prefer explicit validation over silent fallback.
6. Document durable findings if they affect architecture or data contracts.

Common areas to inspect:

- Market data availability.
- Indicator NaN periods.
- Signal generation conditions.
- Scanner filtering thresholds.
- Portfolio history columns.
- Dashboard CSV paths.
