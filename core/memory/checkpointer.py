import logging
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

_checkpointer: BaseCheckpointSaver | None = None


def get_checkpointer() -> BaseCheckpointSaver:
    """Return the conversational checkpointer for LangGraph.
    
    Defaults to MemorySaver which preserves thread state across turns
    indexed by thread_id (WhatsApp phone number).
    """
    global _checkpointer
    if _checkpointer is None:
        # MemorySaver almacena el historial por thread_id (phone_number)
        _checkpointer = MemorySaver()
        logger.info("Initialized in-memory LangGraph checkpointer.")
    return _checkpointer
