# UI Rules

Dashboard UI should support analysis, not decoration.

Prefer:

- Clear sidebar controls.
- Dense but readable tables.
- Interactive Plotly charts.
- Useful hover data.
- Visible metrics tied to reproducible calculations.
- Searchable asset selectors when the candidate universe is large.
- Compact vertical layouts inside the sidebar; keep multi-column metrics and
  wide tables in the main workspace.

Avoid:

- Visual clutter.
- Chart logic that changes business behavior.
- Hidden defaults that materially affect results.
- Overly decorative UI that reduces analytical clarity.
- Long unsearchable dropdowns for ticker or asset selection.
- Dense horizontal metric rows inside narrow sidebar panels.
