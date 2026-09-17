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

RUTA_COMUNIDAD_LOCAL = Path("datos_comunidad.json")
FILE_LOCK = threading.Lock()

# Detectar configuración de Google Cloud Firestore
PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
USE_FIRESTORE = os.getenv("USE_FIRESTORE", "auto").lower()

_firestore_client = None
_firestore_initialized = False


def _init_firestore():
    global _firestore_client, _firestore_initialized
    if _firestore_initialized:
        return _firestore_client

    _firestore_initialized = True

    if USE_FIRESTORE in ["false", "0", "no"]:
        logger.info("Firestore deshabilitado explícitamente vía USE_FIRESTORE=false.")
        return None

    try:
        from google.cloud import firestore
        if PROJECT_ID:
            _firestore_client = firestore.Client(project=PROJECT_ID)
        else:
            _firestore_client = firestore.Client()
        logger.info("Conexión con Google Cloud Firestore inicializada con éxito.")
        return _firestore_client
    except Exception as e:
        logger.warning(f"No se pudo conectar a Google Cloud Firestore ({e}). Usando persistencia local JSON.")
        _firestore_client = None
        return None


def get_storage_backend_info() -> Dict[str, str]:
    """Retorna información del backend de almacenamiento activo."""
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
        "nombre": "JSON Local",
        "icono": "📁",
        "descripcion": f"Almacenamiento local atómico ({RUTA_COMUNIDAD_LOCAL})"
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
            with open(RUTA_COMUNIDAD_LOCAL, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error escribiendo en {RUTA_COMUNIDAD_LOCAL}: {e}")


# =====================================================================
# OPERACIONES PÚBLICAS (HÍBRIDAS FIRESTORE / LOCAL)
# =====================================================================

def cargar_datos_comunidad() -> Dict[str, Any]:
    """Carga votos, opiniones e historial desde Firestore o disco local."""
    client = _init_firestore()
    if client is None:
        return _cargar_datos_local()

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

        # 2. Cargar opiniones (ordenadas por fecha/creación)
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

        # 3. Cargar historial de conversaciones
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
        return _cargar_datos_local()


def registrar_voto(es_positivo: bool) -> Dict[str, Any]:
    """Registra voto de manera atómica con Increment() en Firestore o bloqueo en local."""
    client = _init_firestore()
    if client is None:
        datos = _cargar_datos_local()
        if "votos" not in datos:
            datos["votos"] = {"positivos": 0, "negativos": 0}
        if es_positivo:
            datos["votos"]["positivos"] += 1
        else:
            datos["votos"]["negativos"] += 1
        _guardar_datos_local(datos)
        return datos

    try:
        from google.cloud import firestore
        campo = "positivos" if es_positivo else "negativos"
        doc_ref = client.collection("comunidad").document("votos")
        doc_ref.set({campo: firestore.Increment(1)}, merge=True)
        return cargar_datos_comunidad()
    except Exception as e:
        logger.error(f"Error registrando voto en Firestore: {e}")
        return _cargar_datos_local()


def agregar_opinion(nueva_op: Dict[str, Any]) -> Dict[str, Any]:
    """Añade opinión en la colección de Firestore o lista JSON."""
    client = _init_firestore()
    if client is None:
        datos = _cargar_datos_local()
        datos.setdefault("opiniones", []).append(nueva_op)
        _guardar_datos_local(datos)
        return datos

    try:
        nueva_op_con_ts = dict(nueva_op)
        nueva_op_con_ts["timestamp"] = datetime.utcnow().isoformat()
        client.collection("opiniones").add(nueva_op_con_ts)
        return cargar_datos_comunidad()
    except Exception as e:
        logger.error(f"Error agregando opinión en Firestore: {e}")
        return _cargar_datos_local()


def agregar_conversacion_al_historial(nueva_conv: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda interacción en Firestore o lista JSON."""
    client = _init_firestore()
    if client is None:
        datos = _cargar_datos_local()
        datos.setdefault("historial_conversaciones", []).append(nueva_conv)
        _guardar_datos_local(datos)
        return datos

    try:
        conv_con_ts = dict(nueva_conv)
        conv_con_ts["timestamp"] = datetime.utcnow().isoformat()
        client.collection("historial_conversaciones").add(conv_con_ts)
        return cargar_datos_comunidad()
    except Exception as e:
        logger.error(f"Error registrando conversación en Firestore: {e}")
        return _cargar_datos_local()


def vaciar_historial_conversaciones() -> Dict[str, Any]:
    """Elimina las conversaciones registradas."""
    client = _init_firestore()
    if client is None:
        datos = _cargar_datos_local()
        datos["historial_conversaciones"] = []
        _guardar_datos_local(datos)
        return datos

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
        return _cargar_datos_local()
