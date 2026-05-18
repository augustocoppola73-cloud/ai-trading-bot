# Chart Principles

Dashboard charts should be:

- Readable.
- Interactive.
- Information-dense without clutter.
- Useful for debugging and analysis.
- Consistent with the underlying DataFrame contracts.
- Explicit about whether a control changes visible range or candle interval.

## Preferred Library

Use Plotly for dashboard charts.

## Hover Data

Charts should expose useful context through hover fields rather than forcing the
user to cross-reference tables.

## Avoid

- Decorative charts with weak analytical value.
- Hidden transformations that are not visible in code.
- Chart-specific business logic that belongs in analysis modules.
- Combining visible range and candle interval into one hidden setting.
- Tool controls that rerun the whole page for every drawing-mode change.
