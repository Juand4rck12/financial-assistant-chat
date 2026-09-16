import logging
from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from core.graph.nodes.expense_node import expense_node
from core.graph.nodes.income_node import income_node
from core.graph.nodes.orchestrator import orchestrator_node
from core.graph.nodes.patrimony_node import patrimony_node
from core.graph.nodes.report_node import report_node
from core.graph.state import AgentState
from core.memory.checkpointer import get_checkpointer

logger = logging.getLogger(__name__)

_compiled_graph: CompiledStateGraph | None = None


def route_intent(state: AgentState) -> Literal["expense_node", "income_node", "patrimony_node", "report_node", "__end__"]:
    """Determine the next node based on active intent resolved by orchestrator."""
    intent = state.get("active_intent")
    if intent == "expense":
        return "expense_node"
    if intent == "income":
        return "income_node"
    if intent == "patrimony":
        return "patrimony_node"
    if intent == "report":
        return "report_node"
    return END


def build_financial_graph() -> CompiledStateGraph:
    """Build and compile the multi-agent LangGraph financial workflow."""
    workflow = StateGraph(AgentState)

    # 1. Registrar nodos
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("expense_node", expense_node)
    workflow.add_node("income_node", income_node)
    workflow.add_node("patrimony_node", patrimony_node)
    workflow.add_node("report_node", report_node)

    # 2. Definir punto de entrada
    workflow.set_entry_point("orchestrator")

    # 3. Transiciones condicionales desde el orquestador
    workflow.add_conditional_edges(
        "orchestrator",
        route_intent,
        {
            "expense_node": "expense_node",
            "income_node": "income_node",
            "patrimony_node": "patrimony_node",
            "report_node": "report_node",
            END: END,
        },
    )

    # 4. Los sub-agentes completan su acción y terminan el turno (regla: un turno a la vez)
    workflow.add_edge("expense_node", END)
    workflow.add_edge("income_node", END)
    workflow.add_edge("patrimony_node", END)
    workflow.add_edge("report_node", END)

    # 5. Compilación con Checkpointer de memoria persistente por thread_id
    checkpointer = get_checkpointer()
    compiled = workflow.compile(checkpointer=checkpointer)
    logger.info("Compiled LangGraph Financial Assistant workflow successfully.")
    return compiled


def get_financial_graph() -> CompiledStateGraph:
    """Return singleton instance of the compiled financial graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_financial_graph()
    return _compiled_graph
