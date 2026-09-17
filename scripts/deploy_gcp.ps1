# ==============================================================================
# 🏛️ Script de Aprovisionamiento y Despliegue en Google Cloud Platform (GCP)
# Proyecto: Tecnocracia (Gobierno Multiagente) - Windows PowerShell
# ==============================================================================

[CmdletBinding()]
param (
    [Parameter(Position=0)]
    [string]$ProjectId = $env:GCP_PROJECT_ID,

    [Parameter(Position=1)]
    [string]$Region = "europe-west1"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  🏛️ DESPLIEGUE DE TECNOCRACIA EN GOOGLE CLOUD RUN" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$ScriptDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $ScriptDir

# 1. Parámetros de Configuración
if (-not $ProjectId) {
    $ProjectId = Read-Host "👉 Introduce tu Google Cloud PROJECT_ID"
}

if (-not $ProjectId) {
    Write-Error "❌ Error: Se requiere un PROJECT_ID válido de Google Cloud."
    exit 1
}

$ServiceName = "tecnocracia"

Write-Host "🔹 Proyecto GCP seleccionado: $ProjectId" -ForegroundColor Yellow
Write-Host "🔹 Región de despliegue:      $Region" -ForegroundColor Yellow
Write-Host ""

# 2. Configurar gcloud
Write-Host "⏳ [1/6] Configurando proyecto en gcloud CLI..." -ForegroundColor Gray
gcloud config set project "$ProjectId"

# 3. Habilitar APIs necesarias
Write-Host "⏳ [2/6] Habilitando APIs requeridas en Google Cloud..." -ForegroundColor Gray
gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    firestore.googleapis.com `
    secretmanager.googleapis.com `
    artifactregistry.googleapis.com

# 4. Configurar Base de Datos Firestore en Modo Nativo
Write-Host "⏳ [3/6] Verificando Base de Datos Cloud Firestore..." -ForegroundColor Gray
$fsDbs = gcloud firestore databases list --format="value(name)" 2>$null
if ($fsDbs -notmatch "\(default\)") {
    Write-Host "   Creando base de datos Firestore (Modo Nativo) en la región $Region..." -ForegroundColor Yellow
    try {
        gcloud firestore databases create --location="$Region" --type=firestore-native
    } catch {
        Write-Warning "No se pudo crear la BD de Firestore directamente. Puede que ya esté creada."
    }
} else {
    Write-Host "   ✅ Base de datos Firestore existente y operativa." -ForegroundColor Green
}

# 5. Configurar Secret Manager para GEMINI_API_KEY
Write-Host "⏳ [4/6] Verificando secreto GEMINI_API_KEY en Google Secret Manager..." -ForegroundColor Gray
$secretCheck = gcloud secrets describe GEMINI_API_KEY --project="$ProjectId" 2>$null
if (-not $secretCheck) {
    $geminiKey = $env:GEMINI_API_KEY
    if (-not $geminiKey) {
        $geminiKey = Read-Host "👉 Pega tu GEMINI_API_KEY para guardarla en Secret Manager"
    }
    if ($geminiKey) {
        $geminiKey.Trim() | gcloud secrets create GEMINI_API_KEY --data-file=- --replication-policy="automatic" --project="$ProjectId"
        Write-Host "   ✅ Secreto GEMINI_API_KEY registrado con éxito." -ForegroundColor Green
    } else {
        Write-Warning "No se proporcionó GEMINI_API_KEY. Deberás añadirla más tarde en Secret Manager."
    }
} else {
    Write-Host "   ✅ Secreto GEMINI_API_KEY ya existente en Secret Manager." -ForegroundColor Green
}

# 6. Configurar Cuenta de Servicio y Permisos IAM
Write-Host "⏳ [5/6] Configurando Service Account y Permisos IAM..." -ForegroundColor Gray
$saName = "tecnocracia-runner"
$saEmail = "${saName}@${ProjectId}.iam.gserviceaccount.com"

$saCheck = gcloud iam service-accounts describe "$saEmail" --project="$ProjectId" 2>$null
if (-not $saCheck) {
    gcloud iam service-accounts create "$saName" `
        --display-name="Tecnocracia Cloud Run Service Account" `
        --project="$ProjectId"
}

# Asignar permisos sobre Firestore y Secret Manager
gcloud projects add-iam-policy-binding "$ProjectId" `
    --member="serviceAccount:${saEmail}" `
    --role="roles/datastore.user" >$null 2>&1

gcloud secrets add-iam-policy-binding GEMINI_API_KEY `
    --member="serviceAccount:${saEmail}" `
    --role="roles/secretmanager.secretAccessor" `
    --project="$ProjectId" >$null 2>&1

# 7. Compilar y Desplegar en Google Cloud Run
Write-Host "⏳ [6/6] Compilando imagen y desplegando en Google Cloud Run (Escalado a Cero)..." -ForegroundColor Gray
gcloud run deploy "$ServiceName" `
    --source "$RepoRoot" `
    --project "$ProjectId" `
    --region "$Region" `
    --platform managed `
    --allow-unauthenticated `
    --min-instances 0 `
    --max-instances 10 `
    --memory 1Gi `
    --cpu 1 `
    --service-account "$saEmail" `
    --set-env-vars "GCP_PROJECT_ID=${ProjectId},USE_FIRESTORE=true"

# Obtener URL del servicio
$serviceUrl = gcloud run services describe "$ServiceName" --project="$ProjectId" --region="$Region" --format='value(status.url)'

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  🎉 ¡DESPLIEGUE COMPLETADO CON ÉXITO EN GOOGLE CLOUD!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  🌐 URL Pública de la Aplicación: $serviceUrl" -ForegroundColor Cyan
Write-Host "  🔥 Base de Datos: Google Cloud Firestore (Modo Nativo)" -ForegroundColor Cyan
Write-Host "  🔐 Credenciales: Google Secret Manager" -ForegroundColor Cyan
Write-Host "  ⚡ Escalado: 0 instancias en reposo (coste `$0 cuando no se usa)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Green
