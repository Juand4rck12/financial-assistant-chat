from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state across all nodes in the financial assistant graph."""

    # Historial de mensajes conversacionales gestionado por LangGraph
    messages: Annotated[List[AnyMessage], add_messages]

    # Identificación del usuario
    user_id: Optional[str]
    phone_number: str
    user_name: str

    # Control de intención
    active_intent: Optional[str]  # "expense", "income", "patrimony", "report", "general"

    # Datos parciales de transacción recolectados antes de confirmación
    # Ej: {"type": "expense", "amount": 25000, "category": "Alimentación", "description": "Almuerzo"}
    pending_action: Optional[Dict[str, Any]]

    # Estado de la máquina de confirmación estricta ('Collect before write')
    awaiting_confirmation: bool

    # Respuesta final generada para ser sanitizada y enviada al canal (WhatsApp / Web)
    response_text: Optional[str]
