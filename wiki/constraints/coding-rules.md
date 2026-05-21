# Coding Rules

Prioritize:

- Readability.
- Explicit variable names.
- Small functions.
- Deterministic behavior.
- Clear module boundaries.

Avoid:

- Hidden side effects.
- Premature abstractions.
- Duplicated business logic.
- Broad exception swallowing.
- UI-specific business logic.

Trading logic should remain testable without Streamlit.
