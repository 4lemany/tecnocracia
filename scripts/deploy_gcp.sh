#!/usr/bin/env bash
# ==============================================================================
# 🏛️ Script de Aprovisionamiento y Despliegue en Google Cloud Platform (GCP)
# Proyecto: Tecnocracia (Gobierno Multiagente)
# ==============================================================================

set -e

echo "============================================================"
echo "  🏛️ DESPLIEGUE DE TECNOCRACIA EN GOOGLE CLOUD RUN"
echo "============================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 1. Parámetros de Configuración
PROJECT_ID="${1:-$GCP_PROJECT_ID}"
REGION="${2:-europe-west1}"
SERVICE_NAME="tecnocracia"

if [ -z "$PROJECT_ID" ]; then
    read -p "👉 Introduce tu Google Cloud PROJECT_ID: " PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: Se requiere un PROJECT_ID válido de Google Cloud."
    exit 1
fi

echo "🔹 Proyecto GCP seleccionado: $PROJECT_ID"
echo "🔹 Región de despliegue:      $REGION"
echo ""

# 2. Configurar gcloud
echo "⏳ [1/6] Configurando proyecto en gcloud CLI..."
gcloud config set project "$PROJECT_ID"

# 3. Habilitar APIs necesarias
echo "⏳ [2/6] Habilitando APIs requeridas en Google Cloud..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    firestore.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com

# 4. Configurar Base de Datos Firestore en Modo Nativo
echo "⏳ [3/6] Verificando Base de Datos Cloud Firestore..."
if ! gcloud firestore databases list --format="value(name)" 2>/dev/null | grep -q "(default)"; then
    echo "   Creando base de datos Firestore (Modo Nativo) en la región $REGION..."
    gcloud firestore databases create --location="$REGION" --type=firestore-native || true
else
    echo "   ✅ Base de datos Firestore existente y operativa."
fi

# 5. Configurar Secret Manager para GEMINI_API_KEY
echo "⏳ [4/6] Verificando secreto GEMINI_API_KEY en Google Secret Manager..."
if ! gcloud secrets describe GEMINI_API_KEY --project="$PROJECT_ID" >/dev/null 2>&1; then
    if [ -z "$GEMINI_API_KEY" ]; then
        read -s -p "👉 Pega tu GEMINI_API_KEY para guardarla en Secret Manager: " GEMINI_API_KEY
        echo ""
    fi
    if [ -n "$GEMINI_API_KEY" ]; then
        echo -n "$GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY \
            --data-file=- \
            --replication-policy="automatic" \
            --project="$PROJECT_ID"
        echo "   ✅ Secreto GEMINI_API_KEY registrado con éxito."
    else
        echo "   ⚠️ Advertencia: No se proporcionó GEMINI_API_KEY. Deberás añadirla más tarde en Secret Manager."
    fi
else
    echo "   ✅ Secreto GEMINI_API_KEY ya existente en Secret Manager."
fi

# 6. Configurar Cuenta de Servicio con permisos mínimos
echo "⏳ [5/6] Configurando Service Account y Permisos IAM..."
SA_NAME="tecnocracia-runner"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Tecnocracia Cloud Run Service Account" \
        --project="$PROJECT_ID"
fi

# Asignar permisos sobre Firestore y Secret Manager
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/datastore.user" >/dev/null

gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" >/dev/null 2>&1 || true

# 7. Compilar y Desplegar en Google Cloud Run
echo "⏳ [6/6] Compilando imagen y desplegando en Google Cloud Run (Escalado a Cero)..."
gcloud run deploy "$SERVICE_NAME" \
    --source "$REPO_ROOT" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 10 \
    --memory 1Gi \
    --cpu 1 \
    --service-account "$SA_EMAIL" \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID},USE_FIRESTORE=true"

# Obtener URL del servicio
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')

echo ""
echo "============================================================"
echo "  🎉 ¡DESPLIEGUE COMPLETADO CON ÉXITO EN GOOGLE CLOUD!"
echo "============================================================"
echo "  🌐 URL Pública de la Aplicación: $SERVICE_URL"
echo "  🔥 Base de Datos: Google Cloud Firestore (Modo Nativo)"
echo "  🔐 Credenciales: Google Secret Manager"
echo "  ⚡ Escalado: 0 instancias en reposo (coste $0 cuando no se usa)"
echo "============================================================"
