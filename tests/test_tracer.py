"""
🧪 Tests unitarios para el motor de Observabilidad y Trazabilidad (LLM Tracing & Spans)
Valida la jerarquía de spans, cálculo de latencias y exportación OpenInference / OpenTelemetry.
"""

import unittest
import time
from services.tracer import TraceContext, Span, SpanType, SpanStatus


class TestTracer(unittest.TestCase):

    def test_span_lifecycle_and_duration(self):
        """Valida que un span calcule correctamente su duración en milisegundos."""
        span = Span(name="test_tool", span_type=SpanType.TOOL, inputs={"query": "ipc"})
        time.sleep(0.05)  # 50ms
        span.finish(outputs="IPC: 2.9%", status=SpanStatus.OK)

        self.assertGreaterEqual(span.duration_ms, 40.0)
        self.assertEqual(span.status, SpanStatus.OK)
        self.assertEqual(span.inputs["query"], "ipc")
        self.assertEqual(span.outputs, "IPC: 2.9%")

        d = span.to_dict()
        self.assertIn("span_id", d)
        self.assertEqual(d["name"], "test_tool")
        self.assertEqual(d["duration_ms"], span.duration_ms)

    def test_trace_context_nesting(self):
        """Valida la jerarquía de spans anidados y el contexto de ejecución."""
        trace = TraceContext(trace_name="test_interaction")

        with trace.span("agent_supervisor", SpanType.AGENT) as parent:
            self.assertIsNone(parent.parent_id)

            with trace.span("grounding_tool_ine", SpanType.TOOL, inputs={"metric": "paro"}) as child:
                self.assertEqual(child.parent_id, parent.span_id)
                time.sleep(0.02)
                child.finish(outputs="Tasa Paro: 11.2%")

        trace.finish()

        self.assertEqual(len(trace.spans), 2)
        summary = trace.get_summary()
        self.assertEqual(summary["total_spans"], 2)
        self.assertEqual(summary["tool_calls_count"], 1)
        self.assertEqual(summary["agent_steps_count"], 1)
        self.assertGreater(trace.duration_ms, 15.0)

    def test_trace_error_capture(self):
        """Valida que los errores se capturen sin romper el contexto del trace."""
        trace = TraceContext()
        try:
            with trace.span("failing_span", SpanType.TOOL):
                raise ValueError("Simulated network timeout")
        except ValueError:
            pass

        trace.finish()
        span = trace.spans[0]
        self.assertEqual(span.status, SpanStatus.ERROR)
        self.assertIn("Simulated network timeout", span.error_message)

    def test_token_and_telemetry_aggregation(self):
        """Valida la agregación de tokens y métricas de inferencia."""
        trace = TraceContext()
        with trace.span("gemini_call", SpanType.LLM, metadata={"tokens_in": 120, "tokens_out": 85}):
            pass
        trace.finish()

        summary = trace.get_summary()
        self.assertEqual(summary["tokens_in"], 120)
        self.assertEqual(summary["tokens_out"], 85)
        self.assertEqual(summary["total_tokens"], 205)
        self.assertEqual(summary["llm_calls_count"], 1)


if __name__ == "__main__":
    unittest.main()
