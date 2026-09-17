"""
🏛️ Tecnocracia - Módulo de Persistencia Híbrida (Google Cloud Firestore + Fallback Local)

Permite persistencia resiliente, escalable y stateless en Cloud Run mediante Cloud Firestore,
manteniendo compatibilidad total con almacenamiento local en JSON cuando se ejecuta en desarrollo.
"""

import os
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("tecnocracia.storage")

ROOT_DIR = Path(__file__).resolve().parent.parent
RUTA_COMUNIDAD_LOCAL = ROOT_DIR / "data" / "datos_comunidad.json"
FILE_LOCK = threading.Lock()

# Detectar configuración de almacenamiento
PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
USE_FIRESTORE = os.getenv("USE_FIRESTORE", "false").lower()

# Soporte para persistencia en GitHub Gist (100% Gratuito y sin Google Cloud)
GITHUB_GIST_ID = os.getenv("GITHUB_GIST_ID", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

_firestore_client = None
_firestore_initialized = False


def _get_gist_credentials():
    """Obtiene credenciales de GitHub Gist desde variables de entorno o st.secrets."""
    gist_id = GITHUB_GIST_ID
    token = GITHUB_TOKEN
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if not gist_id:
                gist_id = st.secrets.get("GITHUB_GIST_ID") or st.secrets.get("github_gist_id") or ""
            if not token:
                token = st.secrets.get("GITHUB_TOKEN") or st.secrets.get("github_token") or ""
    except Exception:
        pass
    return gist_id.strip(), token.strip()


def _init_firestore():
    global _firestore_client, _firestore_initialized
    if _firestore_initialized:
        return _firestore_client

    _firestore_initialized = True

    # Si no se activó explícitamente USE_FIRESTORE=true, no intentar conectar a GCP
    if USE_FIRESTORE not in ["true", "1", "yes"]:
        logger.info("Firestore no activado explícitamente. Usando almacenamiento seguro sin GCP.")
        return None

    try:
        from google.cloud import firestore
        project_id = PROJECT_ID
        creds = None

        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                if not project_id:
                    project_id = st.secrets.get("GCP_PROJECT_ID") or st.secrets.get("gcp_project_id") or st.secrets.get("FIREBASE_PROJECT_ID")
                if "gcp_service_account" in st.secrets:
                    from google.oauth2 import service_account
                    sa_info = dict(st.secrets["gcp_service_account"])
                    creds = service_account.Credentials.from_service_account_info(sa_info)
                    if not project_id and "project_id" in sa_info:
                        project_id = sa_info["project_id"]
        except Exception:
            pass

        if creds:
            _firestore_client = firestore.Client(project=project_id, credentials=creds)
        elif project_id:
            _firestore_client = firestore.Client(project=project_id)
        else:
            return None

        logger.info(f"Conexión con Google Cloud Firestore inicializada con éxito (Proyecto: {project_id or 'default'}).")
        return _firestore_client
    except Exception as e:
        logger.warning(f"No se pudo conectar a Google Cloud Firestore ({e}). Usando persistencia local/Gist.")
        _firestore_client = None
        return None


def get_storage_backend_info() -> Dict[str, str]:
    """Retorna información del backend de almacenamiento activo."""
    gist_id, token = _get_gist_credentials()
    if gist_id and token:
        return {
            "tipo": "github_gist",
            "nombre": "GitHub Gist (100% Gratuito y Perpetuo)",
            "icono": "🐙",
            "descripcion": f"Persistencia en nube gratuita de GitHub (Gist: {gist_id[:6]}...). Cero costes y sin Google Cloud."
        }

    client = _init_firestore()
    if client is not None:
        return {
            "tipo": "firestore",
            "nombre": "Google Cloud Firestore",
            "icono": "🔥",
            "descripcion": f"Base de datos NoSQL gestionada en GCP ({PROJECT_ID or 'por defecto'})"
        }
    return {
        "tipo": "json_local",
        "nombre": "JSON Local (Efímero en Streamlit Cloud)",
        "icono": "📁",
        "descripcion": f"Almacenamiento local ({RUTA_COMUNIDAD_LOCAL.name}). Puedes conectar GitHub Gist gratis para que no se borre."
    }


# =====================================================================
# PERSISTENCIA LOCAL (FALLBACK EN DESARROLLO)
# =====================================================================

def _cargar_datos_local() -> Dict[str, Any]:
    with FILE_LOCK:
        datos_default = {
            "votos": {"positivos": 0, "negativos": 0},
            "opiniones": [],
            "historial_conversaciones": []
        }
        if not RUTA_COMUNIDAD_LOCAL.exists():
            try:
                RUTA_COMUNIDAD_LOCAL.parent.mkdir(parents=True, exist_ok=True)
                with open(RUTA_COMUNIDAD_LOCAL, "w", encoding="utf-8") as f:
                    json.dump(datos_default, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return datos_default
        try:
            with open(RUTA_COMUNIDAD_LOCAL, "r", encoding="utf-8") as f:
                datos = json.load(f)
                if "votos" not in datos:
                    datos["votos"] = {"positivos": 0, "negativos": 0}
                if "opiniones" not in datos:
                    datos["opiniones"] = []
                if "historial_conversaciones" not in datos:
                    datos["historial_conversaciones"] = []
                return datos
        except Exception:
            return datos_default


def _guardar_datos_local(datos: Dict[str, Any]) -> None:
    with FILE_LOCK:
        try:
            RUTA_COMUNIDAD_LOCAL.parent.mkdir(parents=True, exist_ok=True)
            with open(RUTA_COMUNIDAD_LOCAL, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error escribiendo en {RUTA_COMUNIDAD_LOCAL}: {e}")


# =====================================================================
# PERSISTENCIA EN GITHUB GIST (100% GRATUITA Y PERPETUA)
# =====================================================================

def _cargar_datos_gist() -> Any:
    gist_id, token = _get_gist_credentials()
    if not gist_id or not token:
        return None
    try:
        import urllib.request
        url = f"https://api.github.com/gists/{gist_id}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Tecnocracia-App"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                files = payload.get("files", {})
                for fname, fcontent in files.items():
                    if "datos_comunidad" in fname or fname.endswith(".json") or len(files) == 1:
                        raw_json = fcontent.get("content", "{}")
                        datos = json.loads(raw_json)
                        if isinstance(datos, dict):
                            datos.setdefault("votos", {"positivos": 0, "negativos": 0})
                            datos.setdefault("opiniones", [])
                            datos.setdefault("historial_conversaciones", [])
                            # Guardar en copia local para acelerar lecturas
                            _guardar_datos_local(datos)
                            return datos
    except Exception as e:
        logger.warning(f"No se pudo sincronizar desde GitHub Gist ({e}). Usando copia local.")
    return None


def _guardar_datos_gist(datos: Dict[str, Any]) -> bool:
    gist_id, token = _get_gist_credentials()
    if not gist_id or not token:
        return False
    try:
        import urllib.request
        url = f"https://api.github.com/gists/{gist_id}"
        body = json.dumps({
            "description": "Tecnocracia - Respaldo Comunitario Gratuito",
            "files": {
                "datos_comunidad.json": {
                    "content": json.dumps(datos, ensure_ascii=False, indent=2)
                }
            }
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
                "User-Agent": "Tecnocracia-App"
            },
            method="PATCH"
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning(f"Error guardando en GitHub Gist ({e}).")
        return False


def _sincronizar_gist_asincrono(datos: Dict[str, Any]):
    """Guarda en Gist en un hilo en segundo plano para no demorar la respuesta de la UI."""
    t = threading.Thread(target=_guardar_datos_gist, args=(datos,), daemon=True)
    t.start()


def _obtener_datos_frescos() -> Dict[str, Any]:
    """Obtiene los datos más actualizados disponibles (Gist remoto si existe o local)."""
    gist_id, token = _get_gist_credentials()
    if gist_id and token:
        datos_remotos = _cargar_datos_gist()
        if datos_remotos is not None:
            return datos_remotos
    return _cargar_datos_local()


# =====================================================================
# OPERACIONES PÚBLICAS (GIST / FIRESTORE / LOCAL)
# =====================================================================

def cargar_datos_comunidad() -> Dict[str, Any]:
    """Carga votos, opiniones e historial desde GitHub Gist, Firestore o disco local."""
    # 1. Prioridad: GitHub Gist (100% gratuito sin GCP, compartido por todos los usuarios)
    datos_gist = _cargar_datos_gist()
    if datos_gist is not None:
        return datos_gist

    # 2. Prioridad: Firestore (solo si se activó explícitamente)
    client = _init_firestore()
    if client is not None:
        try:
            from google.cloud import firestore

            # 1. Cargar votos
            votos_ref = client.collection("comunidad").document("votos").get()
            if votos_ref.exists:
                v_data = votos_ref.to_dict()
                votos = {
                    "positivos": int(v_data.get("positivos", 0)),
                    "negativos": int(v_data.get("negativos", 0))
                }
            else:
                votos = {"positivos": 0, "negativos": 0}

            # 2. Cargar opiniones
            opiniones_docs = (
                client.collection("opiniones")
                .order_by("timestamp", direction=firestore.Query.ASCENDING)
                .limit(100)
                .stream()
            )
            opiniones = []
            for doc in opiniones_docs:
                d = doc.to_dict()
                opiniones.append({
                    "autor": d.get("autor", "Anónimo"),
                    "mensaje": d.get("mensaje", ""),
                    "fecha": d.get("fecha", "")
                })

            # 3. Cargar historial
            historial_docs = (
                client.collection("historial_conversaciones")
                .order_by("timestamp", direction=firestore.Query.ASCENDING)
                .limit(150)
                .stream()
            )
            historial = []
            for doc in historial_docs:
                d = doc.to_dict()
                historial.append({
                    "tipo": d.get("tipo", "Consulta"),
                    "agente": d.get("agente", "Agente"),
                    "pregunta": d.get("pregunta", ""),
                    "respuesta": d.get("respuesta", ""),
                    "fecha": d.get("fecha", ""),
                    "telemetria": d.get("telemetria", {})
                })

            return {
                "votos": votos,
                "opiniones": opiniones,
                "historial_conversaciones": historial
            }
        except Exception as e:
            logger.error(f"Error consultando Firestore: {e}. Recurriendo a datos locales.")

    # 3. Fallback: Archivo JSON local
    return _cargar_datos_local()


def registrar_voto(es_positivo: bool) -> Dict[str, Any]:
    """Registra voto de manera atómica."""
    gist_id, token = _get_gist_credentials()
    client = _init_firestore()

    # Si hay Firestore activo
    if client is not None:
        try:
            from google.cloud import firestore
            campo = "positivos" if es_positivo else "negativos"
            doc_ref = client.collection("comunidad").document("votos")
            doc_ref.set({campo: firestore.Increment(1)}, merge=True)
            return cargar_datos_comunidad()
        except Exception as e:
            logger.error(f"Error registrando voto en Firestore: {e}")

    # En local / Gist: cargar primero datos frescos para sincronizar
    datos = _obtener_datos_frescos()
    if "votos" not in datos:
        datos["votos"] = {"positivos": 0, "negativos": 0}
    if es_positivo:
        datos["votos"]["positivos"] += 1
    else:
        datos["votos"]["negativos"] += 1

    _guardar_datos_local(datos)
    if gist_id and token:
        _sincronizar_gist_asincrono(datos)
    return datos


def agregar_opinion(nueva_op: Dict[str, Any]) -> Dict[str, Any]:
    """Añade opinión en la colección de Firestore o lista JSON/Gist."""
    gist_id, token = _get_gist_credentials()
    client = _init_firestore()

    if client is not None:
        try:
            nueva_op_con_ts = dict(nueva_op)
            nueva_op_con_ts["timestamp"] = datetime.utcnow().isoformat()
            client.collection("opiniones").add(nueva_op_con_ts)
            return cargar_datos_comunidad()
        except Exception as e:
            logger.error(f"Error agregando opinión en Firestore: {e}")

    datos = _obtener_datos_frescos()
    datos.setdefault("opiniones", []).append(nueva_op)
    _guardar_datos_local(datos)
    if gist_id and token:
        _sincronizar_gist_asincrono(datos)
    return datos


def agregar_conversacion_al_historial(nueva_conv: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda interacción en Gist, Firestore o JSON para que todos los usuarios la vean."""
    gist_id, token = _get_gist_credentials()
    client = _init_firestore()

    if client is not None:
        try:
            conv_con_ts = dict(nueva_conv)
            conv_con_ts["timestamp"] = datetime.utcnow().isoformat()
            client.collection("historial_conversaciones").add(conv_con_ts)
            return cargar_datos_comunidad()
        except Exception as e:
            logger.error(f"Error registrando conversación en Firestore: {e}")

    datos = _obtener_datos_frescos()
    datos.setdefault("historial_conversaciones", []).append(nueva_conv)
    _guardar_datos_local(datos)
    if gist_id and token:
        _sincronizar_gist_asincrono(datos)
    return datos


def vaciar_historial_conversaciones() -> Dict[str, Any]:
    """Elimina las conversaciones registradas."""
    gist_id, token = _get_gist_credentials()
    client = _init_firestore()

    if client is not None:
        try:
            batch = client.batch()
            docs = client.collection("historial_conversaciones").limit(200).stream()
            count = 0
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                if count >= 400:
                    batch.commit()
                    batch = client.batch()
                    count = 0
            if count > 0:
                batch.commit()
            return cargar_datos_comunidad()
        except Exception as e:
            logger.error(f"Error vaciando historial en Firestore: {e}")

    datos = _cargar_datos_local()
    datos["historial_conversaciones"] = []
    _guardar_datos_local(datos)
    if gist_id and token:
        _sincronizar_gist_asincrono(datos)
    return datos


def restaurar_datos_comunidad(nuevos_datos: Dict[str, Any]) -> bool:
    """Restaura un backup completo de votos, opiniones e historial."""
    if not isinstance(nuevos_datos, dict):
        return False
    if "votos" not in nuevos_datos or "opiniones" not in nuevos_datos:
        return False

    datos_a_guardar = {
        "votos": nuevos_datos.get("votos", {"positivos": 0, "negativos": 0}),
        "opiniones": nuevos_datos.get("opiniones", []),
        "historial_conversaciones": nuevos_datos.get("historial_conversaciones", [])
    }
    _guardar_datos_local(datos_a_guardar)

    gist_id, token = _get_gist_credentials()
    if gist_id and token:
        _guardar_datos_gist(datos_a_guardar)

    return True


def exportar_datos_comunidad_json() -> str:
    """Exporta los datos actuales en formato JSON formateado para backup."""
    datos = cargar_datos_comunidad()
    return json.dumps(datos, ensure_ascii=False, indent=2)
