import re


def format_whatsapp_text(text: str) -> str:
    """Format and clean text for WhatsApp delivery.
    
    Enforces strict WhatsApp constraints per AGENTS.md:
    - Plain text only.
    - No Markdown (**bold**, _italic_, `code`, # headers, bullet symbols * or -).
    - Preserves newlines and emojis.
    - Preserves numbers, periods and commas.
    """
    if not text:
        return ""

    cleaned = text

    # Eliminar bloques de código markdown
    cleaned = re.sub(r"```[\s\S]*?```", "", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # Eliminar encabezados markdown (# Encabezado)
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)

    # Eliminar negrita y cursiva (**texto**, *texto*, _texto_)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)

    # Reemplazar viñetas de guiones al inicio de línea por texto simple o números
    cleaned = re.sub(r"^\s*[-*]\s+", "• ", cleaned, flags=re.MULTILINE)

    # Normalizar saltos de línea excesivos
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()
