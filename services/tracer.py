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
