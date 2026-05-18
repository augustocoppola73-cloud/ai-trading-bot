# Plotly vs Matplotlib

## Decision

Use Plotly for dashboard visualizations.

## Rationale

The dashboard benefits from interactive charts:

- Unified hover over equity curves.
- Custom hover fields for trade and rotation timelines.
- Responsive Streamlit rendering.
- Better inspection of dense portfolio histories.

Matplotlib remains listed in dependencies, but Plotly is the preferred UI chart
library for timelines, portfolio analytics, and trade visualization.

## Tradeoff

Plotly figures are more verbose than simple Matplotlib plots. The readability
cost is accepted because interactivity is central to analysis.
