# Decision Log

This file records durable architecture and product decisions.

## Current Decisions

| Date | Decision | Rationale | Status |
| --- | --- | --- | --- |
| 2026-05-13 | Use Streamlit as the dashboard layer | Fast iteration for research UI and interactive parameter controls | Active |
| 2026-05-13 | Use Pandas DataFrames as the main data contract | Trading research flows naturally through tabular time series transformations | Active |
| 2026-05-13 | Prefer Plotly for dashboard charts | Interactive hover, timelines, and dense portfolio inspection are important | Active |
| 2026-05-13 | Keep AI scoring deterministic for now | Explainability and reproducibility are more important than opaque autonomy | Active |

## How To Add Decisions

Add decisions when a choice affects architecture, data contracts, workflows,
dependencies, or future maintainability.
