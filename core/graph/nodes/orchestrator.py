import logging
import re
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage

from core.config import settings
from core.graph.state import AgentState
from core.tools.db_tool import get_or_create_user
from db.connection import get_session_factory

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Asistente Financiero personal del usuario en Colombia.
Tu objetivo es ayudarle a organizar sus finanzas personales, registrar gastos, ingresos y consultar su patrimonio en pesos colombianos (COP).

REGLAS ESTRICTAS DE COMUNICACIÓN:
1. Una sola pregunta a la vez: Nunca hagas más de una pregunta en el mismo mensaje.
2. Texto plano para WhatsApp: No utilices Markdown (sin negritas con asteriscos, sin cursivas, sin encabezados con #, sin viñetas de guiones o asteriscos). Usa listas numeradas simples (1. 2.) o texto fluido. Emojis permitidos y recomendados.
3. Prohibido hacer cálculos matemáticos mentales: NUNCA sumes números por tu cuenta. Toda cifra, total, promedio o balance debe provenir de las herramientas del sistema.
4. Tono: Cercano, empático, claro y profesional.
"""


def extract_amount_from_text(text: str) -> Optional[Decimal]:
    """Deterministically extract a monetary amount from natural language text.
    
    Handles:
    - '$25.000', '$ 50000', '15000'
    - '20 mil', '20k' -> 20000
    - '1.5 millones', '2 millones' -> 1500000, 2000000
    """
    clean = text.lower().replace("$", "").strip()

    # Caso 'X millones' o 'X millón'
    mill_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:millones|millon|millón)", clean)
    if mill_match:
        val_str = mill_match.group(1).replace(",", ".")
        try:
            return Decimal(val_str) * Decimal("1000000")
        except Exception:
            pass

    # Caso 'X mil' o 'Xk'
    mil_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:mil|k)\b", clean)
    if mil_match:
        val_str = mil_match.group(1).replace(",", ".")
        try:
            return Decimal(val_str) * Decimal("1000")
        except Exception:
            pass

    # Caso estándar: números con posibles separadores de miles (puntos o comas)
    # Ej: '25.000', '150,000', '45000'
    num_matches = re.findall(r"\b\d{1,3}(?:[.,]\d{3})+(?:\.\d{1,2})?\b|\b\d+(?:\.\d{1,2})?\b", clean)
    for m in num_matches:
        normalized = m.replace(".", "").replace(",", "")
        try:
            val = Decimal(normalized)
            if val > Decimal("0"):
                return val
        except Exception:
            continue

    return None


def detect_category_from_text(text: str) -> str:
    """Categorize expense by common keywords in Spanish."""
    t = text.lower()
    if any(w in t for w in ["almuerzo", "cena", "desayuno", "comida", "mercado", "supermercado", "restaurante", "café", "cafe", "snack"]):
        return "Alimentación"
    if any(w in t for w in ["uber", "taxi", "didi", "pasaje", "gasolina", "peaje", "transmilenio", "metro", "bus", "transporte"]):
        return "Transporte"
    if any(w in t for w in ["luz", "agua", "gas", "internet", "arriendo", "celular", "servicios", "plan"]):
        return "Servicios"
    if any(w in t for w in ["cine", "cerveza", "fiesta", "salida", "juego", "ocio", "rumba"]):
        return "Ocio"
    if any(w in t for w in ["farmacia", "medicina", "médico", "medico", "salud", "cita"]):
        return "Salud"
    if any(w in t for w in ["curso", "libro", "universidad", "estudio"]):
        return "Educación"
    return "Varios"


async def orchestrator_node(state: AgentState) -> dict:
    """Analyze intent, resolve user profile, and route conversation."""
    phone_number = state.get("phone_number") or "+573000000000"
    user_name = state.get("user_name") or "Usuario"

    # 1. Asegurar persistencia del usuario en base de datos
    user_id = state.get("user_id")
    if not user_id:
        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await get_or_create_user(session, phone_number=phone_number, name=user_name)
            user_id = str(user.id)

    # 2. Si hay una confirmación pendiente, continuar en el flujo de confirmación
    if state.get("awaiting_confirmation", False):
        active_intent = state.get("active_intent")
        return {"user_id": user_id, "active_intent": active_intent}

    # 3. Leer mensaje actual del usuario
    messages = state.get("messages", [])
    if not messages:
        return {
            "user_id": user_id,
            "active_intent": "general",
            "response_text": "¡Hola! Soy tu Asistente Financiero. Puedo ayudarte a registrar gastos, ingresos y consultar tu patrimonio. ¿Qué deseas hacer hoy?",
        }

    last_msg = messages[-1].content.strip()
    last_msg_lower = last_msg.lower()

    # 4. Clasificación de Intención
    # A. Consulta de Patrimonio / Cuentas
    if any(w in last_msg_lower for w in ["patrimonio", "cuentas", "cuánto tengo", "cuanto tengo", "deudas", "saldo de mis cuentas", "mis ahorros"]):
        return {
            "user_id": user_id,
            "active_intent": "patrimony",
        }

    # B. Reportes y Balances
    if any(w in last_msg_lower for w in ["resumen", "reporte", "balance", "cuánto he gastado", "cuanto he gastado", "gastos de este", "gastos del mes"]):
        return {
            "user_id": user_id,
            "active_intent": "report",
        }

    # C. Registro de Ingresos
    if any(w in last_msg_lower for w in ["gané", "gane", "recibí", "recibi", "ingreso", "me pagaron", "consignaron", "salario"]):
        amount = extract_amount_from_text(last_msg)
        source = "Salario" if "salario" in last_msg_lower or "nómina" in last_msg_lower else "Ingreso General"
        return {
            "user_id": user_id,
            "active_intent": "income",
            "pending_action": {
                "type": "income",
                "amount": amount,
                "source": source,
                "description": last_msg,
                "date": date.today(),
            },
        }

    # D. Registro de Gastos
    if any(w in last_msg_lower for w in ["gasté", "gaste", "pagué", "pague", "compré", "compre", "costó", "costo", "me costó"]) or (
        extract_amount_from_text(last_msg) is not None and any(w in last_msg_lower for w in ["en ", "de ", "para "])
    ):
        amount = extract_amount_from_text(last_msg)
        category = detect_category_from_text(last_msg)
        return {
            "user_id": user_id,
            "active_intent": "expense",
            "pending_action": {
                "type": "expense",
                "amount": amount,
                "category": category,
                "description": last_msg,
                "date": date.today(),
            },
        }

    # E. Saludo / Conversación General
    if any(w in last_msg_lower for w in ["hola", "buenas", "buenos días", "buenas tardes", "hey"]):
        return {
            "user_id": user_id,
            "active_intent": "general",
            "response_text": f"¡Hola {user_name}! 👋 ¿Cómo van tus finanzas hoy? Puedes decirme cosas como 'Gasté 25.000 en almuerzo', '¿Cuánto he gastado este mes?' o '¿Cuál es mi patrimonio?'.",
        }

    # Fallback general con Mistral o respuesta orientadora
    if settings.mistral_api_key:
        try:
            from langchain_mistralai import ChatMistralAI
            llm = ChatMistralAI(
                model=settings.mistral_model,
                api_key=settings.mistral_api_key,
                temperature=0.2,
            )
            prompt = f"{SYSTEM_PROMPT}\nMensaje del usuario: {last_msg}\nResponde en texto plano brevemente."
            ai_res = await llm.ainvoke([HumanMessage(content=prompt)])
            return {
                "user_id": user_id,
                "active_intent": "general",
                "response_text": ai_res.content,
            }
        except Exception as err:
            logger.warning("Mistral AI call failed (%s). Using deterministic fallback.", err)

    return {
        "user_id": user_id,
        "active_intent": "general",
        "response_text": "Puedo ayudarte a registrar un gasto (ej: 'Pagué 30.000 en gasolina'), un ingreso ('Recibí 500.000') o consultar tu balance ('¿Cuánto he gastado este mes?'). ¿Qué deseas hacer?",
    }
