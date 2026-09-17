# ☁️ Guía de Despliegue en Google Cloud con Coste Cero (Always Free Tier)

Esta guía explica detalladamente cómo poner en marcha **CI/CD con GitHub Actions**, **Google Cloud Run** y **Google Cloud Functions** garantizando que **no haya ningún cargo económico (0,00 €)** en tu cuenta de Google Cloud Platform (GCP).

---

## 1. 🛡️ La Garantía de Coste Cero: GCP Always Free Tier

Google Cloud incluye una serie de servicios en su **nivel perpetuamente gratuito (Always Free Tier)**:

| Servicio | Límite Siempre Gratuito (Cada Mes) | Configuración en Tecnocracia |
| :--- | :--- | :--- |
| **Cloud Run** | 2.000.000 peticiones, 360.000 GiB-segundos de RAM, 180.000 vCPU-segundos | `--min-instances 0` (Escala a 0 cuando nadie lo usa), `--max-instances 1`, 512MiB RAM |
| **Cloud Functions** | 2.000.000 de llamadas al mes, 400.000 GB-segundos | Gen 2 / HTTP serverless con escala a 0 |
| **Cloud Build** | 120 minutos de compilación al día (máquina `e2-standard-2`) | Pipeline nativo `cloudbuild.yaml` |
| **GitHub Actions** | Ilimitado para repos públicos; 2.000 min/mes en privados | `ci.yml` (Pruebas) y `cd-cloud-run.yml` (Despliegue) |
| **Artifact Registry** | 0.5 GB de almacenamiento al mes | Limpieza automática de imágenes antiguas |

---

## 2. 🚨 Medida de Protección Preventiva: Alerta de Presupuesto (0,01 €)

Antes de desplegar, crea una alerta de presupuesto en GCP para que te avise por email si se detectara el más mínimo coste:

1. Entra en la consola de Google Cloud: **Facturación (Billing) > Presupuestos y alertas (Budgets & alerts)**.
2. Pulsa en **Crear presupuesto**.
3. Dale el nombre `Alerta Coste Cero`.
4. En **Importe objetivo**, introduce `1,00 €` (o `0,01 €`).
5. En umbrales de alerta, configura notificaciones al **1%**, **50%** y **100%**.
6. Marca la casilla para recibir correos electrónicos de notificación.

---

## 3. ⚙️ Preparación del Proyecto en Google Cloud

Puedes ejecutar estos comandos desde tu terminal local (si tienes `gcloud` instalado) o directamente desde la consola **Google Cloud Shell** (el botón de terminal arriba a la derecha en la web de GCP):

### Paso 3.1. Definir variables
```bash
export PROJECT_ID="tu-id-de-proyecto-gcp"
export REGION="europe-west1"
gcloud config set project $PROJECT_ID
```

### Paso 3.2. Habilitar las APIs necesarias (gratuitas)
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  cloudfunctions.googleapis.com
```

### Paso 3.3. Crear el repositorio en Artifact Registry
```bash
gcloud artifacts repositories create tecnocracia-repo \
  --repository-format=docker \
  --location=$REGION \
  --description="Repositorio Docker para Tecnocracia"
```

### Paso 3.4. Crear la Service Account para GitHub Actions
```bash
# Crear cuenta de servicio
gcloud iam service-accounts create github-deployer \
  --description="Service account para CI/CD desde GitHub Actions" \
  --display-name="GitHub Deployer"

# Asignar roles mínimos requeridos
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Generar clave JSON para GitHub Secrets
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=github-deployer@$PROJECT_ID.iam.gserviceaccount.com
```

> ⚠️ Guarda el contenido de `sa-key.json` de forma segura y **nunca lo subas a git** (está protegido en `.gitignore`).

---

## 4. 🔑 Configurar Secretos en GitHub

En tu repositorio de GitHub (`https://github.com/4lemany/tecnocracia`):

1. Ve a **Settings > Secrets and variables > Actions**.
2. Pulsa en **New repository secret** y añade los siguientes 3 secretos:

| Nombre del Secreto | Valor |
| :--- | :--- |
| `GCP_PROJECT_ID` | Tu ID de proyecto en Google Cloud (ej: `tecnocracia-gov`) |
| `GCP_SA_KEY` | Todo el contenido del archivo `sa-key.json` generado en el paso 3.4 |
| `GEMINI_API_KEY` | Tu API Key de Google Gemini |

---

## 5. 🚀 Funcionamiento del CI/CD

Una vez configurados los secretos:

1. **Cada vez que subes código (`git push origin main`) o creas un Pull Request**:
   - `.github/workflows/ci.yml` se ejecuta automáticamente:
     - Instala dependencias.
     - Pasa el linter `ruff`.
     - Ejecuta las 8 pruebas unitarias (`pytest tests/ -v`).
     - Realiza una compilación de prueba del `Dockerfile`.
2. **Al fusionar en la rama `main`**:
   - `.github/workflows/cd-cloud-run.yml` se activa:
     - Autentica con Google Cloud sin exponer contraseñas.
     - Compila y sube la imagen a Artifact Registry.
     - Despliega la aplicación en **Cloud Run** con:
       - `--min-instances 0` (Se duerme si no hay visitas = 0€).
       - `--max-instances 1` (Protección contra picos).
       - `--memory 512Mi` (Free tier).
     - Te muestra la URL HTTPS pública directa para acceder a tu plataforma.

---

## 6. ⚡ Despliegue de la Cloud Function (Microservicio Serverless)

Si deseas además desplegar la función serverless HTTP para consultas directas a los ministros:

```bash
cd cloud_functions/consultar_gabinete

gcloud functions deploy consultar-gabinete \
  --gen2 \
  --runtime=python312 \
  --region=europe-west1 \
  --source=. \
  --entry-point=consultar_gabinete \
  --trigger-http \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=1 \
  --memory=256Mi \
  --set-env-vars=GEMINI_API_KEY=tu_clave_gemini
```

### Probar la Cloud Function:
```bash
curl -X POST https://europe-west1-TU_PROYECTO.cloudfunctions.net/consultar-gabinete \
  -H "Content-Type: application/json" \
  -d '{"agente": "economia", "pregunta": "¿Cuál es la tasa de inflación oficial?"}'
```

---

## 7. 🧹 Buenas Prácticas de Mantenimiento a Coste Cero

- **Limpieza de imágenes**: Artifact Registry ofrece 0.5 GB gratis al mes. La imagen construida ocupa ~120 MB comprimida. Mantén un máximo de 2-3 versiones para estar siempre dentro del cupo gratuito.
- **Scale to Zero**: Cloud Run apaga los contenedores tras un par de minutos de inactividad, garantizando consumo nulo.
