# 🏛️ Tecnocracia: Partido Político y Gabinete Multiagente

Sistema multiagente desarrollado con **Google ADK** y **Gemini** para modelar un gobierno tecnocrático, donde cada ministro analiza las problemáticas regionales desde su área de especialización y debate mediante datos y métricas contrastables.

---

## 📂 Estructura del Proyecto

```text
tecnocracia/
├── .github/workflows/
│   ├── ci.yml                     # CI: Linter, tests unitarios y ADK evals
│   └── cd-cloud-run.yml           # CD: Despliegue continuo a Cloud Run
├── primer_ministro/
│   ├── agent.py                   # Agente orquestador (Primer Ministro)
│   ├── evals_primer_ministro.json # Casos de prueba automatizados
│   └── test_prime_minister.ipynb  # Notebook interactivo del Consejo de Ministros
├── ministros/                     # Módulos de subagentes especializados
│   ├── __init__.py                # Exportación del gabinete
│   ├── economia.py                # Ministro de Economía y Hacienda (+ APIs INE/BdE/BOE)
│   ├── educacion.py               # Ministro de Educación y Ciencia (+ APIs Educabase/Eurostat)
│   └── interior.py                # Ministro de Interior (+ APIs Interior/AEMET/DGT)
├── tests/
│   └── test_adk_evals.py          # Batería de pruebas automatizadas
├── app.py                         # Aplicación Web Streamlit (UI, Métricas, Trazabilidad)
├── storage.py                     # Persistencia híbrida (Cloud Firestore + JSON Local)
├── secrets_manager.py             # Gestión de secretos (Secret Manager + .env)
├── deploy_gcp.sh                  # Script de despliegue en 1 clic (Bash / Linux / Mac)
├── deploy_gcp.ps1                 # Script de despliegue en 1 clic (PowerShell / Windows)
├── Dockerfile                     # Imagen contenedor optimizada para Cloud Run
├── cloudbuild.yaml                # Pipeline declarativo para Google Cloud Build
├── requirements.txt               # Dependencias del proyecto
└── README.md
```

---

## 🚀 Guía de Inicio Rápido: Clonar y Desplegar en Google Cloud

Si acabas de clonar este repositorio, sigue estos pasos para ponerlo en producción en **Google Cloud Run** en cuestión de minutos.

### 1. Requisitos Previos

1. **Google Cloud SDK (`gcloud` CLI)** instalado en tu equipo. ([Descargar gcloud](https://cloud.google.com/sdk/docs/install)).
2. **Una cuenta de Google Cloud** con un proyecto creado (ej: `mi-proyecto-tecnocracia`).
3. **Una API Key de Gemini** obtenida gratuitamente en [Google AI Studio](https://aistudio.google.com/).
4. Haber iniciado sesión en tu terminal con tu cuenta de Google:
   ```bash
   gcloud auth login
   ```

---

### 2. Clonar el Repositorio

```bash
git clone https://github.com/4lemany/tecnocracia.git
cd tecnocracia
```

---

### 3. Despliegue en 1 Clic (Aprovisionamiento Automático)

Ejecuta el script correspondiente a tu sistema operativo. El script se encargará de:
* Habilitar todas las APIs de GCP necesarias (`run`, `firestore`, `secretmanager`, `cloudbuild`, `artifactregistry`).
* Crear la base de datos **Cloud Firestore** en modo Nativo para persistencia *stateless*.
* Registrar tu **`GEMINI_API_KEY` en Google Secret Manager** de forma cifrada.
* Configurar la cuenta de servicio con permisos de mínimo privilegio.
* Compilar el contenedor y desplegarlo en **Cloud Run** con **escalado a cero** ($0 en reposo).

#### 🪟 En Windows (PowerShell):
```powershell
.\deploy_gcp.ps1 -ProjectId "TU_PROJECT_ID" -Region "europe-west1"
```
*(Si no pasas los parámetros, el script te los preguntará de forma interactiva).*

#### 🐧 En Linux / macOS / Google Cloud Shell (Bash):
```bash
chmod +x deploy_gcp.sh
./deploy_gcp.sh TU_PROJECT_ID europe-west1
```

Al finalizar, la consola te devolverá la **URL pública HTTPS** lista para compartir.

---

## 💻 Ejecución Local (Desarrollo)

Si deseas probar o modificar la aplicación en tu máquina local antes de desplegar:

### 1. Crear y activar el entorno virtual
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Crea un archivo `.env` en la raíz copiando el ejemplo:
```env
GEMINI_API_KEY="tu_clave_de_gemini_aqui"
```

### 4. Lanzar la aplicación
```bash
streamlit run app.py
```
Abre tu navegador en `http://localhost:8501`. En entorno local, la aplicación conmutará de forma automática y transparente a almacenamiento atómico en `datos_comunidad.json`.

### 5. Ejecutar la batería de pruebas
```bash
python tests/test_adk_evals.py
```

---

## ⚙️ Configuración de CI/CD en GitHub Actions

Si subes este proyecto a tu propio repositorio de GitHub, puedes activar el despliegue continuo automático ante cada `git push` a la rama `main`:

1. Ve a tu repositorio en GitHub: **Settings > Secrets and variables > Actions**.
2. Añade los siguientes **Repository Secrets**:
   * `GCP_PROJECT_ID`: El ID de tu proyecto en Google Cloud.
   * `GEMINI_API_KEY`: Tu clave de API de Gemini.
   * `GCP_SA_KEY`: La clave en formato JSON de tu Service Account con permisos de despliegue en Cloud Run (puedes generarla con `gcloud iam service-accounts keys create`).
   * *(Opcional)* `GCP_REGION`: Región de despliegue (por defecto: `europe-west1`).

Con esto configurado, cada vez que hagas `git push` a `main`:
1. El workflow [`.github/workflows/ci.yml`](file:///.github/workflows/ci.yml) ejecutará los linters y la batería de tests.
2. Si los tests pasan, [`.github/workflows/cd-cloud-run.yml`](file:///.github/workflows/cd-cloud-run.yml) compilará la imagen y actualizará el servicio en Google Cloud Run sin caídas de servicio.

---

## 🤖 Roles de los Agentes

* **Prime Minister (Supervisor):** Coordina el gabinete, plantea los problemas regionales, arbitra los debates entre ministros y emite el dictamen final junto con el comunicado público.
* **Ministro de Economía:** Optimización presupuestaria, análisis de ROI, sostenibilidad fiscal y atracción de inversiones (con herramientas en tiempo real del INE, Banco de España y BOE).
* **Ministro de Educación:** Formación de capital humano, competencias STEM, I+D y pedagogía basada en evidencia (con herramientas de Educabase, Eurostat y SIIU).
* **Ministro de Interior:** Seguridad predictiva, digitalización radical y eficiencia de infraestructuras cívicas (con herramientas de Interior, AEMET y DGT).
