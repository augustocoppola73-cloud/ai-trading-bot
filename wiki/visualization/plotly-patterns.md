# Plotly Patterns

Current Plotly usage is direct and explicit through `plotly.graph_objects`.

## Existing Patterns

- `go.Figure()`
- `plotly.subplots.make_subplots` for asset focus charts with a price panel and
  a volume subpanel.
- `go.Scatter` for lines and markers.
- `go.Candlestick` for technical asset charts.
- `go.Bar` for volume under price candles.
- `add_hline` for current price and other programmatic reference levels.
- `hovermode="x unified"` for equity comparisons.
- `hovermode="x"` plus spike lines for trading-board style price charts.
- `customdata` plus `hovertemplate` for richer timeline inspection.
- `st.plotly_chart(..., use_container_width=True)` for Streamlit rendering.

## Trading Chart Pattern

Asset focus charts separate visible range from candle interval. The visible
range controls how much history is shown, while the candle interval controls
bar granularity such as 5m, 15m, 1h, 4h, 1d, or 1wk. Keep this separation so
short-range charts do not collapse into one oversized daily candle.

Use Plotly native interaction features for the current bridge implementation:

- `dragmode="pan"` for navigation.
- `dragmode="zoom"` for box zoom.
- `dragmode="drawline"` for manual trendlines.
- `dragmode="drawrect"` for marking price/time areas.
- `modeBarButtonsToAdd` with drawing and erase tools. Prefer the modebar for
  tool switching because Streamlit widgets rerun the page.
- `scrollZoom=True` for mouse-wheel zoom.
- `doubleClick="reset+autosize"` for quick chart reset.
- `uirevision`, `selectionrevision`, `editrevision`, and a stable
  `st.plotly_chart` key to reduce unwanted loss of zoom/drawing state across
  Streamlit reruns.

Keep Plotly drawing tools conservative. Line, rectangle, and erase are more
reliable than broad freeform drawing sets in the current Streamlit wrapper.
Avoid adding many drawing modes if they make user annotations disappear or hard
to delete.

Current technical overlays include trend moving averages, EMA 20/50/200, SMA
50/200, VWAP, and Bollinger bands.

## Chart Engine Boundary

Plotly is still the fallback engine for asset focus charts, but professional
manual analysis should prefer the KLineCharts pro beta component. KLineCharts
supports K-line focused interactions and built-in overlays such as segment,
ray, straight line, price line, price channel, parallel lines, and Fibonacci
line. It is embedded with `components.html`, so chart tool changes happen
inside the iframe and do not trigger Streamlit reruns.

KLineCharts currently depends on a CDN script in the HTML component. If offline
support becomes required, vendor the minified library locally or build a proper
Streamlit custom component package.

## Known Plotly Limits

Plotly drawing tools are useful for lightweight annotation, but they are not a
full professional trading-board toolset. In particular:

- Manual Fibonacci retracement is not native.
- A ruler that measures price/time distance while dragging is not native.
- Persisting user drawings requires additional state capture.
- Streamlit widgets around the chart rerun the page, so chart tool selection
  should stay inside the Plotly modebar whenever possible.

If manual Fibonacci, ruler, persistent drawings, and fast drawing workflows
become central, evaluate a dedicated JavaScript chart component such as
KLineCharts or a TradingView-style charting integration.

## Preferred Style

Keep chart construction readable. If a chart becomes large or reused, consider
extracting a pure function that accepts a DataFrame and returns a Plotly figure.
