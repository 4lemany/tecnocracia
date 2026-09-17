"""
🏛️ Tecnocracia - Módulos de Servicios Centrales
Proporciona persistencia híbrida, gestión segura de secretos y motor de evaluación ADK.
"""

from .storage import (
    cargar_datos_comunidad,
    agregar_conversacion_al_historial,
    registrar_voto,
    agregar_opinion,
    vaciar_historial_conversaciones,
    get_storage_backend_info,
)
from .secrets_manager import (
    get_gemini_api_key,
    get_secrets_backend_info,
)
from .evaluacion import (
    evaluar_respuesta_adk,
)
from .tracer import (
    TraceContext,
    Span,
    SpanType,
    SpanStatus,
    diagnosticar_error_gemini,
)

__all__ = [
    "cargar_datos_comunidad",
    "agregar_conversacion_al_historial",
    "registrar_voto",
    "agregar_opinion",
    "vaciar_historial_conversaciones",
    "get_storage_backend_info",
    "get_gemini_api_key",
    "get_secrets_backend_info",
    "evaluar_respuesta_adk",
    "TraceContext",
    "Span",
    "SpanType",
    "SpanStatus",
    "diagnosticar_error_gemini",
]
