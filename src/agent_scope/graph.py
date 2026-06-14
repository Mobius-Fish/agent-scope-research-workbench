from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .agents.critic import critic_node
from .agents.perspective import perspective_node
from .agents.planner import planner_node
from .agents.researcher import researcher_node
from .agents.reviser import reviser_node
from .agents.supervisor import route_after_supervisor, supervisor_node
from .agents.verifier import verifier_node
from .agents.writer import writer_node
from .state import ResearchState


def build_graph():
    """Build workflow with supervisor loop and critic/revision stage."""

    graph = StateGraph(ResearchState)

    graph.add_node("perspective", perspective_node)
    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("writer", writer_node)
    graph.add_node("critic", critic_node)
    graph.add_node("reviser", reviser_node)

    graph.add_edge(START, "perspective")
    graph.add_edge("perspective", "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "verifier")
    graph.add_edge("verifier", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "researcher": "researcher",
            "writer": "writer",
        },
    )
    graph.add_edge("writer", "critic")
    graph.add_edge("critic", "reviser")
    graph.add_edge("reviser", END)

    return graph.compile()
