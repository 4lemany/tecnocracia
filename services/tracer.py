"""
🔬 Tecnocracia - Módulo de Observabilidad y Trazabilidad de Agentes (LLM Tracing & Spans)

Proporciona telemetría distribuida compatible con estándares de la industria (OpenInference / OpenTelemetry)
para inspeccionar la orquestación de agentes Google ADK, ejecución de herramientas oficiales (Grounding),
llamadas a LLM y evaluaciones de calidad.
"""

import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import contextmanager


def diagnosticar_error_gemini(e: Exception) -> Dict[str, Any]:
    """
    Analiza y diagnostica excepciones ocurridas durante la llamada al SDK de Gemini
    (google.genai.errors.ServerError, ClientError, 429, 500, 503, cuotas, safety, etc.)
    ofreciendo una explicación causal (Explainable AI / DevOps Root Cause) y recomendaciones prácticas.
    """
    err_str = str(e)
    err_type = type(e).__name__

    # 0. Modelo no encontrado o descatalogado por Google (404 NOT_FOUND)
    if any(k in err_str for k in ["404", "NOT_FOUND", "not found", "no longer available", "models/"]):
        return {
            "categoria": "MODELO_NO_DISPONIBLE",
            "titulo": "Modelo de Gemini Descatalogado o No Disponible",
            "codigo_tecnico": "HTTP 404 - NOT_FOUND",
            "explicacion": (
                "La versión del modelo solicitada ha sido retirada o no está disponible para nuevos usuarios en la API de Google AI Studio. "
                "Google recomienda utilizar 'gemini-3.6-flash' para disfrutar de las últimas mejoras y soporte oficial."
            ),
            "accion_recomendada": "Se ha actualizado automáticamente a gemini-3.6-flash. Vuelve a enviar tu pregunta.",
            "es_transitorio": False,
            "icono": "📦",
            "color_badge": "#eab308",
            "detalle_tecnico": f"{err_type}: {err_str[:250]}"
        }

    # 1. Límite de cuota / Rate limit (429 / RESOURCE_EXHAUSTED)
    if any(k in err_str for k in ["429", "RESOURCE_EXHAUSTED", "quota", "QuotaExceeded", "rate limit", "RateLimit"]):
        return {
            "categoria": "CUOTA_EXCEDIDA",
            "titulo": "Límite de Peticiones por Minuto Alcanzado (Rate Limit)",
            "codigo_tecnico": "HTTP 429 - RESOURCE_EXHAUSTED",
            "explicacion": (
                "La API de Google Gemini en su nivel gratuito (Free Tier) impone un límite estricto de "
                "15 peticiones por minuto (RPM) y 1.500 peticiones diarias. Al interactuar de forma sucesiva "
                "o al orquestar varios agentes y herramientas en poco tiempo, se superó transitoriamente esta tasa."
            ),
            "accion_recomendada": (
                "Pausa 15-20 segundos para restablecer la cuota, o vincula tu clave gratuita de Groq (30 RPM / 0,00 €) "
                "o una segunda clave de Gemini para disfrutar de failover automático continuo sin interrupciones."
            ),
            "es_transitorio": True,
            "icono": "🚦",
            "color_badge": "#f59e0b",
            "detalle_tecnico": f"{err_type}: {err_str[:250]}"
        }

    # 1.1 Error de autenticación en Groq Cloud
    if "Groq" in err_str and any(k in err_str for k in ["401", "invalid_api_key", "invalid_request_error"]):
        return {
            "categoria": "AUTENTICACION_INVALIDA",
            "titulo": "Clave API de Groq Cloud Inválida",
            "codigo_tecnico": "GROQ_401 - INVALID_API_KEY",
            "explicacion": "La clave de Groq configurada no es válida o ha sido revocada.",
            "accion_recomendada": "Copia una clave válida desde console.groq.com/keys e introdúcela en el panel de redundancia.",
            "es_transitorio": False,
            "icono": "🔑",
            "color_badge": "#ef4444",
            "detalle_tecnico": f"{err_type}: {err_str[:250]}"
        }

    # 2. Sobrecarga temporal de servidores de Google Cloud (500 / 503 / 504 / ServerError)
    if any(k in err_str for k in ["ServerError", "500", "503", "504", "overloaded", "UNAVAILABLE", "InternalServerError"]):
        return {
            "categoria": "SOBRECARGA_SERVIDOR",
            "titulo": "Servidores de Google Cloud Temporalmente Saturados",
            "codigo_tecnico": "HTTP 503 / ServerError - Transient Overload",
            "explicacion": (
                "El clúster de cómputo de Google que procesa el modelo Gemini está experimentando picos de alta demanda "
                "o rebalanceo de infraestructura en la región. No es un error en tu código ni en tu pregunta; "
                "los servidores de inferencia rechazaron transitoriamente la conexión."
            ),
            "accion_recomendada": "Pulsa 'Reintentar Consulta'. Suele resolverse automáticamente en pocos segundos una vez Google equilibra la carga.",
            "es_transitorio": True,
            "icono": "☁️",
            "color_badge": "#ef4444",
            "detalle_tecnico": f"{err_type}: {err_str[:250]}"
        }

    # 3. Moderación y Filtro de Seguridad Ético (Safety Block)
    if any(k in err_str for k in ["SAFETY", "blocked", "finish_reason", "HarmCategory", "BlockedPromptException", "Recitation"]):
        return {
            "categoria": "FILTRO_SEGURIDAD",
            "titulo": "Moderación de Seguridad y Directrices Éticas Activada",
            "codigo_tecnico": "FinishReason: SAFETY_BLOCK",
            "explicacion": (
                "Los filtros de seguridad y alineamiento de Google Gemini clasificaron los términos de la consulta o "
                "la respuesta generada bajo una categoría sensible (como integridad cívica, polarización política extrema "
                "o contenidos regulados)."
            ),
            "accion_recomendada": "Reformula la pregunta evitando términos polémicos directos y planteándola desde una perspectiva de análisis técnico e institucional.",
            "es_transitorio": False,
            "icono": "🛡️",
            "color_badge": "#ec4899",
            "detalle_tecnico": f"{err_type}: {err_str[:250]}"
        }

    # 4. Fallo de Autenticación o Clave Inválida (401 / 403 / API_KEY_INVALID)
    if any(k in err_str for k in ["API_KEY_INVALID", "401", "403", "PERMISSION_DENIED", "unauthorized"]):
        return {
            "categoria": "AUTENTICACION_INVALIDA",
            "titulo": "Clave de API de Gemini Inválida o Sin Permisos",
            "codigo_tecnico": "HTTP 401/403 - PERMISSION_DENIED",
            "explicacion": (
                "La clave de API proporcionada no es válida, ha caducado o no tiene habilitado el acceso "
                "a los modelos de Gemini en Google AI Studio o Google Cloud Vertex."
            ),
            "accion_recomendada": "Comprueba tu clave GEMINI_API_KEY en los Secrets de Streamlit o en el archivo .env local.",
            "es_transitorio": False,
            "icono": "🔑",
            "color_badge": "#dc2626",
            "detalle_tecnico": f"{err_type}: {err_str[:250]}"
        }

    # 5. Fallo de Conexión de Red o Timeout
    if any(k in err_str for k in ["Timeout", "timed out", "ConnectionError", "Network", "Failed to establish"]):
        return {
            "categoria": "TIMEOUT_CONEXION",
            "titulo": "Fallo de Conexión de Red o Tiempo de Espera Agotado",
            "codigo_tecnico": "NETWORK_TIMEOUT",
            "explicacion": (
                "Se agotó el tiempo de espera al conectar con el endpoint remoto de Google Gemini. "
                "Puede deberse a latencia elevada en la red o corte temporal de salida a internet."
            ),
            "accion_recomendada": "Comprueba la conexión de red e inténtalo de nuevo en unos momentos.",
            "es_transitorio": True,
            "icono": "🔌",
            "color_badge": "#f97316",
            "detalle_tecnico": f"{err_type}: {err_str[:250]}"
        }

    # 6. Incidencia Genérica
    return {
        "categoria": "ERROR_GENERICO",
        "titulo": "Incidencia Inesperada en la Inferencia de IA",
        "codigo_tecnico": f"EXCEPTION_{err_type}",
        "explicacion": (
            "Se ha producido una excepción imprevista durante el ciclo de procesamiento de la respuesta con Google GenAI."
        ),
        "accion_recomendada": "Revisa los detalles técnicos en la traza de observabilidad o prueba a reformular la consulta.",
        "es_transitorio": True,
        "icono": "⚠️",
        "color_badge": "#64748b",
        "detalle_tecnico": f"{err_type}: {err_str[:250]}"
    }


class SpanType:
    AGENT = "agent"
    TOOL = "tool"
    LLM = "llm"
    EVAL = "eval"
    ROUTING = "routing"


class SpanStatus:
    OK = "OK"
    ERROR = "ERROR"


class Span:
    """Unidad atómica de ejecución (Span) en la traza de un sistema multiagente."""

    def __init__(
        self,
        name: str,
        span_type: str = SpanType.AGENT,
        parent_id: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.span_id: str = f"span-{uuid.uuid4().hex[:8]}"
        self.parent_id: Optional[str] = parent_id
        self.name: str = name
        self.span_type: str = span_type
        self.inputs: Dict[str, Any] = inputs or {}
        self.outputs: Any = None
        self.metadata: Dict[str, Any] = metadata or {}
        self.status: str = SpanStatus.OK
        self.error_message: Optional[str] = None

        self.start_time: float = time.perf_counter()
        self.start_iso: str = datetime.now().isoformat()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0

    def finish(
        self,
        outputs: Any = None,
        status: str = SpanStatus.OK,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Span":
        """Finaliza el span calculando la duración exacta en milisegundos."""
        self.end_time = time.perf_counter()
        self.duration_ms = round((self.end_time - self.start_time) * 1000.0, 2)
        if outputs is not None:
            self.outputs = outputs
        if metadata:
            self.metadata.update(metadata)
        if error:
            self.status = SpanStatus.ERROR
            self.error_message = str(error)
        else:
            self.status = status
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el span a diccionario JSON-friendly."""
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "span_type": self.span_type,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "start_time": self.start_iso,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "error": self.error_message,
            "metadata": self.metadata,
        }


class TraceContext:
    """Gestor de traza que orquesta la jerarquía de Spans durante una interacción."""

    def __init__(self, trace_name: str = "tecnocracia_query", user_id: str = "citizen"):
        self.trace_id: str = f"tr-{uuid.uuid4().hex[:12]}"
        self.trace_name: str = trace_name
        self.user_id: str = user_id
        self.start_time: float = time.perf_counter()
        self.start_iso: str = datetime.now().isoformat()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0

        self.spans: List[Span] = []
        self._span_stack: List[Span] = []

    def start_span(
        self,
        name: str,
        span_type: str = SpanType.AGENT,
        inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Inicia un nuevo span anidado en el contexto activo."""
        parent_id = self._span_stack[-1].span_id if self._span_stack else None
        span = Span(
            name=name,
            span_type=span_type,
            parent_id=parent_id,
            inputs=inputs,
            metadata=metadata,
        )
        self.spans.append(span)
        self._span_stack.append(span)
        return span

    def end_span(
        self,
        outputs: Any = None,
        status: str = SpanStatus.OK,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Span]:
        """Finaliza el span más reciente del stack activo."""
        if not self._span_stack:
            return None
        span = self._span_stack.pop()
        span.finish(outputs=outputs, status=status, error=error, metadata=metadata)
        return span

    @contextmanager
    def span(
        self,
        name: str,
        span_type: str = SpanType.AGENT,
        inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Context manager para medición automática de bloques de ejecución."""
        s = self.start_span(name, span_type, inputs=inputs, metadata=metadata)
        try:
            yield s
            if s.end_time is None:
                self.end_span()
        except Exception as e:
            if s.end_time is None:
                self.end_span(error=e, status=SpanStatus.ERROR)
            raise e

    def finish(self) -> "TraceContext":
        """Cierra la traza completa."""
        while self._span_stack:
            self.end_span()
        self.end_time = time.perf_counter()
        self.duration_ms = round((self.end_time - self.start_time) * 1000.0, 2)
        return self

    def get_summary(self) -> Dict[str, Any]:
        """Calcula métricas agregadas de rendimiento para analítica DevOps."""
        tool_spans = [s for s in self.spans if s.span_type == SpanType.TOOL]
        llm_spans = [s for s in self.spans if s.span_type == SpanType.LLM]
        agent_spans = [s for s in self.spans if s.span_type == SpanType.AGENT]

        total_tokens_in = sum(s.metadata.get("tokens_in", 0) for s in llm_spans)
        total_tokens_out = sum(s.metadata.get("tokens_out", 0) for s in llm_spans)

        return {
            "trace_id": self.trace_id,
            "total_duration_ms": self.duration_ms,
            "total_spans": len(self.spans),
            "tool_calls_count": len(tool_spans),
            "llm_calls_count": len(llm_spans),
            "agent_steps_count": len(agent_spans),
            "tokens_in": total_tokens_in,
            "tokens_out": total_tokens_out,
            "total_tokens": total_tokens_in + total_tokens_out,
            "estimated_cost_usd": 0.0,  # 0.00€ Always Free Tier
        }

    def to_dict(self) -> Dict[str, Any]:
        """Exporta la traza completa a estructura estándar de observabilidad."""
        if self.end_time is None:
            self.finish()
        return {
            "trace_id": self.trace_id,
            "trace_name": self.trace_name,
            "user_id": self.user_id,
            "start_time": self.start_iso,
            "total_duration_ms": self.duration_ms,
            "summary": self.get_summary(),
            "spans": [s.to_dict() for s in self.spans],
        }
