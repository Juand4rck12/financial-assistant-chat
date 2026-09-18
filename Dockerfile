FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Optimizar compilación de bytecode y modo de instalación
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

# 1. Copiar primero definiciones de dependencias para aprovechar la caché de Docker
COPY pyproject.toml uv.lock ./

# 2. Instalar dependencias de producción (sin paquetes de desarrollo)
RUN uv sync --frozen --no-dev --no-install-project

# 3. Copiar el código fuente de la aplicación
COPY . .

# 4. Sincronizar el proyecto
RUN uv sync --frozen --no-dev

# Render inyecta la variable $PORT automáticamente (usualmente 10000)
EXPOSE 8000

# Ejecutar migraciones de Alembic al arrancar y levantar Uvicorn
CMD ["sh", "-c", "uv run alembic upgrade head && exec uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
