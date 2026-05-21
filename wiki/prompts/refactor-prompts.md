# Refactor Prompts

## Safe Refactor Proposal

```text
Analyze the current implementation first.
Propose a minimal refactor that preserves behavior.
List impacted modules, DataFrame contracts, risks, and verification steps.
Wait for approval before editing.
```

## Data Contract Refactor

```text
Identify every module that reads or writes the affected columns.
Propose a migration path that preserves backward compatibility where possible.
Do not rename columns or change generated CSV format without approval.
```
