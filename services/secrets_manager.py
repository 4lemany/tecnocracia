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
        _CACHE_SECRETS[secret_name] = valor_env
        return valor_env

    # 3. Streamlit Secrets (si se ejecuta dentro de Streamlit)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and secret_name in st.secrets:
            val = str(st.secrets[secret_name])
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
            secreto_str = response.payload.data.decode("UTF-8").strip()
            if secreto_str:
                _CACHE_SECRETS[secret_name] = secreto_str
                logger.info(f"Secreto '{secret_name}' obtenido exitosamente desde Google Secret Manager.")
                return secreto_str
        except Exception as e:
            logger.warning(f"No se pudo obtener '{secret_name}' desde Secret Manager: {e}")

    return default


def get_gemini_api_key() -> Optional[str]:
    """Retorna la API Key de Gemini desde Secret Manager o entorno local."""
    return get_secret("GEMINI_API_KEY")


def get_secrets_backend_info() -> Dict[str, str]:
    """Retorna información sobre el origen de las credenciales activas."""
    api_key = get_gemini_api_key()
    if not api_key:
        return {
            "estado": "no_configurada",
            "origen": "Ninguno",
            "icono": "⚠️",
            "mensaje": "Clave GEMINI_API_KEY no detectada."
        }

    # Determinar procedencia
    if PROJECT_ID and secret_in_gcp("GEMINI_API_KEY"):
        return {
            "estado": "activa",
            "origen": "Google Secret Manager",
            "icono": "🔐",
            "mensaje": f"Gestionada en la nube (Proyecto GCP: {PROJECT_ID})"
        }
    return {
        "estado": "activa",
        "origen": ".env / Entorno Local",
        "icono": "📄",
        "mensaje": "Cargada desde configuración local"
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
