# Imagen base ligera oficial de Python 3.12
FROM python:3.12-slim

# Evitar escritura de bytecode y habilitar buffer inmediato de logs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    STREAMLIT_SERVER_PORT=8080 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Instalar curl para healthchecks de Cloud Run
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Crear usuario no privilegiado para seguridad
RUN addgroup --system appgroup && adduser --system --group appuser

# Copiar dependencias primero para optimizar la caché de capas de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY app.py .
COPY datos_comunidad.json .
COPY ministros/ ministros/
COPY primer_ministro/ primer_ministro/

# Ajustar permisos para que el usuario no privilegiado pueda escribir en datos_comunidad.json
RUN chown -R appuser:appgroup /app

# Cambiar a usuario no privilegiado
USER appuser

# Exponer el puerto por defecto de Cloud Run
EXPOSE 8080

# Healthcheck interno del servidor Streamlit
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/_stcore/health || exit 1

# Comando de arranque adaptado dinámicamente a la variable $PORT de Google Cloud Run
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
