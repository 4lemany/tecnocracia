"""
🏛️ Tecnocracia - Módulo de Gestión Segura de Credenciales (Google Secret Manager + Fallback Local)

Permite recuperar claves y secretos sensibles directamente desde Google Cloud Secret Manager
en entornos de producción (Cloud Run), manteniendo compatibilidad con .env y st.secrets en desarrollo.
"""

import os
import logging
from typing import Optional, Dict

logger = logging.getLogger("tecnocracia.secrets")

_CACHE_SECRETS: Dict[str, str] = {}
PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")


def get_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """Obtiene un secreto priorizando variables de entorno locales, st.secrets y Google Secret Manager."""
    # 1. Caché en memoria
    if secret_name in _CACHE_SECRETS:
        return _CACHE_SECRETS[secret_name]

    # 2. Variable de entorno local (.env / sistema)
    valor_env = os.getenv(secret_name)
    if valor_env:
        val_clean = valor_env.strip().strip('"').strip("'")
        _CACHE_SECRETS[secret_name] = val_clean
        return val_clean

    # 3. Streamlit Secrets (si se ejecuta dentro de Streamlit)
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if secret_name in st.secrets:
                val = str(st.secrets[secret_name]).strip().strip('"').strip("'")
                _CACHE_SECRETS[secret_name] = val
                return val
            for k in st.secrets:
                if str(k).upper() == secret_name.upper():
                    val = str(st.secrets[k]).strip().strip('"').strip("'")
                    _CACHE_SECRETS[secret_name] = val
                    return val
    except Exception:
        pass

    # 4. Google Cloud Secret Manager
    if PROJECT_ID:
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            resource_name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": resource_name})
            secreto_str = response.payload.data.decode("UTF-8").strip().strip('"').strip("'")
            if secreto_str:
                _CACHE_SECRETS[secret_name] = secreto_str
                logger.info(f"Secreto '{secret_name}' obtenido exitosamente desde Google Secret Manager.")
                return secreto_str
        except Exception as e:
            logger.warning(f"No se pudo obtener '{secret_name}' desde Secret Manager: {e}")

    return default


def get_gemini_api_key() -> Optional[str]:
    """Retorna la API Key de Gemini desde Secret Manager, st.secrets, .env o st.session_state."""
    try:
        import streamlit as st
        if hasattr(st, "session_state") and st.session_state.get("custom_gemini_api_key"):
            return str(st.session_state.custom_gemini_api_key).strip().strip('"').strip("'")
    except Exception:
        pass
    key = get_secret("GEMINI_API_KEY")
    return str(key).strip().strip('"').strip("'") if key else None


def get_secondary_gemini_api_key() -> Optional[str]:
    """Retorna una segunda clave de Gemini para failover automático si la primera agota el rate limit de 15 RPM."""
    try:
        import streamlit as st
        if hasattr(st, "session_state") and st.session_state.get("custom_gemini_api_key_2"):
            return str(st.session_state.custom_gemini_api_key_2).strip().strip('"').strip("'")
    except Exception:
        pass
    key = get_secret("GEMINI_API_KEY_2")
    return str(key).strip().strip('"').strip("'") if key else None


def get_groq_api_key() -> Optional[str]:
    """Retorna la API Key de Groq (100% gratuita, 30 RPM) para failover automático o motor primario."""
    try:
        import streamlit as st
        if hasattr(st, "session_state") and st.session_state.get("custom_groq_api_key"):
            return str(st.session_state.custom_groq_api_key).strip().strip('"').strip("'")
    except Exception:
        pass
    # Intentar con varios nombres posibles en secrets
    for nombre_var in ["GROQ_API_KEY", "GROQ_KEY", "GROQ"]:
        key = get_secret(nombre_var)
        if key:
            return str(key).strip().strip('"').strip("'")
    return None


def get_secrets_backend_info() -> Dict[str, str]:
    """Retorna información sobre el origen de las credenciales activas y estado de redundancia."""
    api_key = get_gemini_api_key()
    groq_key = get_groq_api_key()
    gemini_2_key = get_secondary_gemini_api_key()

    redundancia_txt = []
    if groq_key:
        redundancia_txt.append("🚀 Groq LPU (Activo)")
    if gemini_2_key:
        redundancia_txt.append("⚡ Gemini Secundario (Activo)")

    if not api_key and not groq_key:
        return {
            "estado": "no_configurada",
            "origen": "Ninguno",
            "icono": "⚠️",
            "mensaje": "Sin claves de inferencia configuradas.",
            "redundancia": "Desactivada"
        }

    origen = ".env / Entorno Local"
    icono = "📄"
    if PROJECT_ID and secret_in_gcp("GEMINI_API_KEY"):
        origen = "Google Secret Manager"
        icono = "🔐"

    return {
        "estado": "activa",
        "origen": origen,
        "icono": icono,
        "mensaje": "Cargada desde configuración activa",
        "redundancia": " + ".join(redundancia_txt) if redundancia_txt else "Ninguna (Solo Gemini Primario)",
        "tiene_groq": bool(groq_key),
        "tiene_gemini_2": bool(gemini_2_key)
    }


def secret_in_gcp(secret_name: str) -> bool:
    """Verifica de forma rápida si el secreto existe en Secret Manager."""
    if not PROJECT_ID:
        return False
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{secret_name}"
        client.get_secret(request={"name": name})
        return True
    except Exception:
        return False
