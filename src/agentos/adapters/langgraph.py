from __future__ import annotations

from dataclasses import dataclass

from agentos.workflows import SimpleWorkflow


@dataclass(frozen=True, slots=True)
class LangGraphAdapter:
    """Adapter boundary for compiling AgentOS workflows into LangGraph graphs."""

    workflow: SimpleWorkflow

    def describe(self) -> dict[str, object]:
        """Return LangGraph-ready workflow metadata without compiling a graph."""
        return {
            "engine": "langgraph",
            "workflow": self.workflow.name,
            "steps": [step.name for step in self.workflow.steps],
        }
