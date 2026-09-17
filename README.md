# 🏛️ Tecnocracia: Partido Político y Gabinete Multiagente

Sistema multiagente desarrollado con **Google ADK** y **Gemini** para modelar un gobierno tecnocrático, donde cada ministro analiza las problemáticas regionales desde su área de especialización y debate mediante datos y métricas contrastables.

---

## 📂 Estructura del Proyecto

```text
tecnocracia/
├── .venv/                         # Entorno virtual gestionado por uv (Python 3.12)
├── .python-version                # Versión fijada a 3.12
├── .env                           # Configuración de variables de entorno (GEMINI_API_KEY)
├── .vscode/
│   └── settings.json              # Configuración del IDE (Jedi Language Server)
├── primer_ministro/
│   └── test_prime_minister.ipynb  # Notebook interactivo del Consejo de Ministros
├── ministros/                     # Módulos de subagentes especializados
│   ├── __init__.py                # Exportación del gabinete
│   ├── economia.py                # Ministro de Economía y Hacienda
│   ├── educacion.py               # Ministro de Educación y Ciencia
│   └── interior.py                # Ministro de Interior y Gobernanza Digital
└── README.md
```

---

## 🚀 Puesta en Marcha

### 1. Configurar la clave de API
Edita el archivo `.env` en la raíz del proyecto y añade tu API Key de Gemini:
```env
GEMINI_API_KEY="tu_clave_de_gemini"
```

### 2. Ejecutar el Notebook
Abre [`primer_ministro/test_prime_minister.ipynb`](file:///c:/Users/adri/Desktop/tecnocracia/primer_ministro/test_prime_minister.ipynb) en tu editor, selecciona el kernel `.venv` (`Python 3.12.13`) y ejecuta las celdas secuencialmente.

---

## 🤖 Roles de los Agentes

* **Prime Minister (Supervisor):** Coordina el gabinete, plantea los problemas regionales, arbitra los debates entre ministros y emite el dictamen final junto con el comunicado público.
* **Ministro de Economía:** Optimización presupuestaria, análisis de ROI, sostenibilidad fiscal y atracción de inversiones.
* **Ministro de Educación:** Formación de capital humano, competencias STEM, I+D y pedagogía basada en evidencia.
* **Ministro de Interior:** Seguridad predictiva, digitalización radical y eficiencia de infraestructuras cívicas.

---

## ☁️ CI/CD y Despliegue en Google Cloud (Always Free Tier / Coste Cero)

El proyecto cuenta con una infraestructura completa de integración y entrega continua configurada para operar estrictamente dentro del **tramo gratuito perpetuo (0,00 €)** de Google Cloud y GitHub Actions:

* **Integración Continua (CI):** [.github/workflows/ci.yml](file:///.github/workflows/ci.yml) ejecuta automáticamente linter, pruebas unitarias (`pytest`) y validación del contenedor Docker en cada push o pull request.
* **Despliegue Continuo (CD):** [.github/workflows/cd-cloud-run.yml](file:///.github/workflows/cd-cloud-run.yml) compila y despliega la aplicación en **Google Cloud Run** con escala a cero (`--min-instances 0`) y límite de seguridad (`--max-instances 1`).
* **Cloud Build Nativo:** [cloudbuild.yaml](file:///cloudbuild.yaml) para compilar y desplegar usando los 120 minutos diarios gratuitos de GCP.
* **Microservicio Serverless:** [cloud_functions/consultar_gabinete/](file:///cloud_functions/consultar_gabinete/) función HTTP Cloud Function Gen 2 para consultas API directas al gabinete.
* **Guía Completa de Configuración:** Consulta [docs/GCP_FREE_TIER_SETUP.md](file:///docs/GCP_FREE_TIER_SETUP.md) para los pasos de configuración y activación de la alerta de presupuesto de 0€.
