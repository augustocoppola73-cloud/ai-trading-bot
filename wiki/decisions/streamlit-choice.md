# Streamlit Choice

## Decision

Use Streamlit as the application dashboard framework.

## Rationale

Streamlit fits the current project because it supports:

- Fast research iteration.
- Sidebar controls for parameters.
- DataFrame display.
- Plotly integration.
- Simple local execution.

## Tradeoff

Streamlit can encourage mixing UI, orchestration, and business logic in one
file. The project should actively keep trading logic in modules under `src/`
and avoid embedding strategy behavior directly in Streamlit callbacks.
