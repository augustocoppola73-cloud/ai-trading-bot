# AI Agent Rules

AI agents must follow the project governance contract.

## Never

- Modify source code without explicit approval.
- Install dependencies without approval.
- Perform large refactors automatically.
- Silently change business logic.
- Introduce hidden dependencies.
- Duplicate logic across modules.
- Optimize at the expense of readability.

## Always For Significant Tasks

1. Analyze.
2. Propose.
3. Wait for approval.
4. Implement only the approved scope.
5. Verify.
6. Summarize.

## Orchestrator Parallelism

When the user invokes `@Orchestrator`, always evaluate whether the task can be
split across parallel sub-agents.

Use parallel sub-agents when responsibilities are independent, such as market
data analysis, dashboard UX, QA, documentation, performance review, or
architecture review.

Do not use parallel sub-agents when the task is small, tightly coupled, or
would cause multiple agents to edit the same file without clear ownership.

The orchestrator remains responsible for integration, conflict resolution,
wiki compliance, verification, and the final user-facing summary.

## Multi-Agent Transparency

When `@Orchestrator` uses sub-agents, the final response should include a
compact agent exchange log showing:

- Agent name.
- Assigned task.
- Context read.
- Key findings.
- Handoff to the orchestrator.
- Integration decision.

Do not expose hidden chain-of-thought. Summarize reasoning as evidence,
decisions, assumptions, and unresolved questions.
