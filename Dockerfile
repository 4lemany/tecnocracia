# 🏛️ Dockerfile optimizado para Tecnocracia en Google Cloud Run
FROM python:3.12-slim

# Evitar que Python escriba archivos .pyc y forzar salida inmediata en stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente de la aplicación
COPY . .

# Puerto expuesto por defecto en Cloud Run (8080)
EXPOSE 8080

# Healthcheck para verificar el arranque correcto de Streamlit
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/_stcore/health || exit 1

# Comando de arranque adaptado a la variable $PORT dinámica de Cloud Run
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false --server.headless=true"]
