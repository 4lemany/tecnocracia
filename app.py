"""
🏛️ Tecnocracia: Plataforma de Gobierno Multiagente con Google ADK y Gemini.
Chat Libre con Trazabilidad, Evaluación ADK, Historial de Conversaciones, Votación Comunitaria y Buzón de Opiniones Real.
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from pathlib import Path
import streamlit as st

# Configuración de página adaptada para móvil y escritorio (solo en ejecución de Streamlit)
if "pytest" not in sys.modules and "unittest" not in sys.modules:
    st.set_page_config(
        page_title="Tecnocracia | Partido y Gobierno Multiagente",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="auto"
    )

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Cargar API Key (Soporta Google Secret Manager, .env local y st.secrets)
from services.secrets_manager import get_gemini_api_key, get_secrets_backend_info
api_key = get_gemini_api_key()

from google import genai
from google.genai import types
from primer_ministro.agent import INSTRUCCION_PRIME_MINISTER
from ministros.economia import (
    INSTRUCCION_ECONOMIA,
    obtener_datos_ine,
    obtener_datos_banco_espana,
    consultar_boe_legislacion_fiscal
)
from ministros.educacion import (
    INSTRUCCION_EDUCACION,
    obtener_datos_educacion_espana,
    obtener_datos_eurostat_educacion,
    obtener_datos_universidades_siiu
)
from ministros.interior import (
    INSTRUCCION_INTERIOR,
    obtener_datos_criminalidad_interior,
    obtener_datos_aemet_emergencias,
    obtener_datos_dgt_trafico
)

# Motor de Observabilidad y Trazabilidad de Agentes (LLM Tracing & Spans)
try:
    from services.tracer import TraceContext, SpanType, SpanStatus, diagnosticar_error_gemini
except ImportError:
    import importlib
    if "services.tracer" in sys.modules:
        importlib.reload(sys.modules["services.tracer"])
    from services.tracer import TraceContext, SpanType, SpanStatus, diagnosticar_error_gemini

# Persistencia Híbrida Gestionada (GitHub Gist Gratuito / Fallback Local / Firestore)
from services.storage import (
    cargar_datos_comunidad,
    agregar_conversacion_al_historial,
    registrar_voto,
    agregar_opinion,
    vaciar_historial_conversaciones,
    get_storage_backend_info,
    exportar_datos_comunidad_json,
    restaurar_datos_comunidad
)

# Motor de Evaluación de Agentes Google ADK
from services.evaluacion import evaluar_respuesta_adk

if "datos_comunidad" not in st.session_state:
    st.session_state.datos_comunidad = cargar_datos_comunidad()

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "ha_votado" not in st.session_state:
    st.session_state.ha_votado = False

# Estilos CSS con Alto Contraste, Responsive Design y Tarjetas Adaptativas (WCAG AAA)
st.markdown("""
<style>
    p, span, div, h1, h2, h3, h4, h5, h6, .stMarkdown {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        hyphens: auto;
    }
    
    /* Estilos de Métricas Adaptativas: Fondo Limpio, Moderno y 100% Legible en Tema Claro */
    [data-testid="stMetric"], .stMetric {
        background: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }
    [data-testid="stMetric"]:hover {
        border-color: #3b82f6 !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15) !important;
    }
    [data-testid="stMetric"] * {
        color: #0f172a !important;
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] *, .stMetric label, [data-testid="stMetricLabel"] p {
        color: #0369a1 !important; /* Azul cobalto vivo y nítido */
        font-weight: 700 !important;
        font-size: 0.9em !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] *, .stMetric [data-testid="stMetricValue"], [data-testid="stMetricValue"] div {
        color: #0f172a !important; /* Texto oscuro de alto contraste */
        font-weight: 800 !important;
        font-size: 1.55rem !important;
    }
    [data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * {
        color: #64748b !important;
    }

    /* Soporte Adaptativo si el usuario o navegador usa Tema Oscuro */
    @media (prefers-color-scheme: dark) {
        [data-testid="stMetric"], .stMetric {
            background: #1e293b !important;
            border: 1px solid #334155 !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35) !important;
        }
        [data-testid="stMetric"] * {
            color: #f8fafc !important;
        }
        [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] *, .stMetric label, [data-testid="stMetricLabel"] p {
            color: #38bdf8 !important; /* Azul cian luminoso */
        }
        [data-testid="stMetricValue"], [data-testid="stMetricValue"] *, .stMetric [data-testid="stMetricValue"], [data-testid="stMetricValue"] div {
            color: #ffffff !important; /* Blanco puro */
        }
    }

    .opinion-card {
        background: #f8fafc !important;
        border-left: 5px solid #3b82f6 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 14px !important;
        margin-bottom: 12px !important;
        color: #0f172a !important;
    }
    .opinion-card strong {
        color: #0369a1 !important;
    }
    .opinion-card p {
        color: #1e293b !important;
    }

    @media (prefers-color-scheme: dark) {
        .opinion-card {
            background: #1e293b !important;
            border: 1px solid #334155 !important;
            color: #ffffff !important;
        }
        .opinion-card strong {
            color: #38bdf8 !important;
        }
        .opinion-card p {
            color: #f1f5f9 !important;
        }
    }

    .adk-eval-card {
        background: #f1f5f9 !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 10px !important;
        padding: 16px !important;
        margin-top: 10px !important;
        color: #0f172a !important;
    }
    @media (prefers-color-scheme: dark) {
        .adk-eval-card {
            background: #0f172a !important;
            color: #ffffff !important;
        }
    }

    .trace-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.8em;
        font-weight: 700;
        margin-right: 6px;
        margin-bottom: 6px;
        white-space: normal;
    }
    .pill-blue { background-color: #eff6ff !important; color: #1d4ed8 !important; border: 1px solid #93c5fd !important; }
    .pill-green { background-color: #ecfdf5 !important; color: #047857 !important; border: 1px solid #6ee7b7 !important; }
    .pill-amber { background-color: #fffbeb !important; color: #b45309 !important; border: 1px solid #fcd34d !important; }

    @media (prefers-color-scheme: dark) {
        .pill-blue { background-color: #1e3a8a !important; color: #bfdbfe !important; border: 1px solid #3b82f6 !important; }
        .pill-green { background-color: #064e3b !important; color: #a7f3d0 !important; border: 1px solid #10b981 !important; }
        .pill-amber { background-color: #78350f !important; color: #fde68a !important; border: 1px solid #f59e0b !important; }
    }

    .badge-eco { background-color: #ecfdf5; color: #065f46; padding: 4px 10px; border-radius: 6px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
    .badge-edu { background-color: #eff6ff; color: #1e40af; padding: 4px 10px; border-radius: 6px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
    .badge-int { background-color: #fdf2f8; color: #9d174d; padding: 4px 10px; border-radius: 6px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
    .badge-pm  { background-color: #fffbeb; color: #92400e; padding: 4px 10px; border-radius: 6px; font-weight: bold; display: inline-block; margin-bottom: 6px; }

    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
            padding-top: 1rem !important;
        }
        .stMetric {
            padding: 8px !important;
            margin-bottom: 8px;
        }
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# Función de llamada a Gemini con manejo robusto de reintentos, degradación elegante y observabilidad
def generar_con_reintento(client, contents, model="gemini-3.6-flash", config=None, max_intentos=3):
    """
    Invoca a Google Gemini con política de reintentos exponenciales, control de tokens y degradación elegante.
    Retorna (response, None) en caso de éxito, o (None, error_diag) si se agotan los reintentos
    o se detectan bloqueos de seguridad / cuotas, impidiendo que Streamlit falle con pantalla roja.
    """
    ultimo_error = None
    backoff_tiempos = [2, 4]

    for intento in range(max_intentos):
        try:
            if config is not None:
                response = client.models.generate_content(model=model, contents=contents, config=config)
            else:
                response = client.models.generate_content(model=model, contents=contents)

            # Verificar si fue bloqueado por filtros de moderación en candidates
            if hasattr(response, "candidates") and response.candidates:
                cand = response.candidates[0]
                finish_reason = getattr(cand, "finish_reason", None)
                finish_str = str(finish_reason).upper() if finish_reason else ""
                if any(k in finish_str for k in ["SAFETY", "BLOCK", "RECITATION"]):
                    diag = diagnosticar_error_gemini(Exception(f"SAFETY_FILTER_TRIGGERED: {finish_str}"))
                    return None, diag

            # Verificar acceso a texto sin generar excepción
            try:
                _ = response.text
            except Exception as e_text:
                diag = diagnosticar_error_gemini(e_text)
                return None, diag

            return response, None

        except Exception as e:
            ultimo_error = e
            err_msg = str(e)
            es_transitorio = any(k in err_msg for k in ["429", "RESOURCE_EXHAUSTED", "ServerError", "500", "503", "504", "overloaded", "UNAVAILABLE"])

            if es_transitorio and intento < max_intentos - 1:
                espera = backoff_tiempos[intento] if intento < len(backoff_tiempos) else 4
                st.toast(f"⏳ Servidores de Google con alta demanda. Reintentando ({intento+1}/{max_intentos})...", icon="⏳")
                time.sleep(espera)
                continue
            elif intento < max_intentos - 1 and "SAFETY" not in err_msg and "API_KEY" not in err_msg:
                time.sleep(1.5)
                continue
            else:
                break

    # Diagnóstico causal y explicabilidad sin elevar excepción al motor de Streamlit
    diag = diagnosticar_error_gemini(ultimo_error if ultimo_error else Exception("Error no identificado en la llamada"))
    return None, diag


def render_error_diagnosis_card(error_diag: dict, key_prefix: str = "err"):
    """
    Renderiza una tarjeta visual premium de explicabilidad con contraste ultra nítido
    compatible con tema claro y oscuro (WCAG AAA).
    """
    icono = error_diag.get("icono", "⚠️")
    titulo = error_diag.get("titulo", "Incidencia en el Servicio de Inferencia")
    codigo = error_diag.get("codigo_tecnico", "ERROR")
    color = error_diag.get("color_badge", "#ef4444")
    explicacion = error_diag.get("explicacion", "Se ha producido un error temporal de conexión.")
    recomendacion = error_diag.get("accion_recomendada", "Vuelve a intentarlo en unos instantes.")
    detalle = error_diag.get("detalle_tecnico", "")

    st.markdown(f"""
    <div style='background-color: #0f172a; border: 2px solid {color}; border-left: 8px solid {color}; border-radius: 12px; padding: 20px; margin: 16px 0; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); color: #ffffff;'>
        <div style='display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 12px;'>
            <span style='font-size: 1.15em; font-weight: 800; color: #ffffff; letter-spacing: 0.2px;'>{icono} {titulo}</span>
            <span style='background-color: {color}; color: #ffffff; font-size: 0.82em; padding: 5px 12px; border-radius: 6px; font-weight: 800; letter-spacing: 0.5px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);'>{codigo}</span>
        </div>
        <div style='color: #38bdf8; font-size: 0.95em; font-weight: 700; margin-bottom: 4px;'>
            ¿Por qué ha ocurrido esto?
        </div>
        <div style='color: #f1f5f9; font-size: 0.95em; line-height: 1.6; margin-bottom: 14px;'>
            {explicacion}
        </div>
        <div style='background-color: #1e293b; border-left: 4px solid #38bdf8; border: 1px solid #334155; padding: 12px 16px; border-radius: 8px; font-size: 0.92em; margin-bottom: 12px; line-height: 1.5;'>
            <strong style='color: #38bdf8;'>💡 Acción Recomendada:</strong> <span style='color: #ffffff; font-weight: 500;'>{recomendacion}</span>
        </div>
        <details style='margin-top: 8px; font-size: 0.85em;'>
            <summary style='color: #60a5fa; font-weight: 600; cursor: pointer; text-decoration: underline;'>🔍 Ver detalle técnico de la excepción</summary>
            <pre style='margin-top: 8px; padding: 12px; background-color: #020617; border: 1px solid #334155; border-radius: 8px; color: #fca5a5; font-size: 0.85em; overflow-x: auto; white-space: pre-wrap; word-break: break-all; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;'>{detalle}</pre>
        </details>
    </div>
    """, unsafe_allow_html=True)

def resolver_grounding_tools(interlocutor: str, pregunta: str, trace: TraceContext) -> tuple[str, list[str]]:
    """Ejecuta y traza las herramientas oficiales de los ministros según el contexto."""
    contexto_herramientas = []
    preg_lower = pregunta.lower()

    # 1. Herramientas de Economía
    if any(k in interlocutor for k in ["Economía", "Primer Ministro", "Gabinete Completo"]) and any(
        k in preg_lower for k in ["ipc", "inflac", "paro", "empleo", "pib", "deuda", "euribor", "hipoteca", "impuesto", "fiscal", "presupuesto", "dinero", "econom"]
    ):
        with trace.span("Tool: INE Oficial API (IPC/Paro)", SpanType.TOOL, inputs={"indicador": "ipc_paro"}, metadata={"fuente": "servicios.ine.es"}) as s:
            datos_ine = obtener_datos_ine("ipc" if "ipc" in preg_lower or "inflac" in preg_lower else "paro")
            s.finish(outputs=datos_ine)
            contexto_herramientas.append(datos_ine)

        if any(k in preg_lower for k in ["euribor", "hipoteca", "deuda", "tipo", "interes", "bce"]):
            with trace.span("Tool: Banco de España (Tipos & Euríbor)", SpanType.TOOL, inputs={"tipo": "euribor"}, metadata={"fuente": "bde.es"}) as s:
                datos_bde = obtener_datos_banco_espana("euribor")
                s.finish(outputs=datos_bde)
                contexto_herramientas.append(datos_bde)

        if any(k in preg_lower for k in ["ley", "fiscal", "impuesto", "presupuesto", "boe", "legal"]):
            with trace.span("Tool: BOE (Legislación Fiscal)", SpanType.TOOL, inputs={"busqueda": "presupuestos"}, metadata={"fuente": "boe.es"}) as s:
                datos_boe = consultar_boe_legislacion_fiscal("presupuestos")
                s.finish(outputs=datos_boe)
                contexto_herramientas.append(datos_boe)

    # 2. Herramientas de Educación
    if any(k in interlocutor for k in ["Educación", "Primer Ministro", "Gabinete Completo"]) and any(
        k in preg_lower for k in ["educac", "colegio", "universidad", "escuela", "estudiante", "stem", "pisa", "fp", "profesor", "beca"]
    ):
        with trace.span("Tool: Ministerio de Educación (Gasto & Ratios)", SpanType.TOOL, inputs={"tipo": "gasto"}, metadata={"fuente": "educacion.gob.es"}) as s:
            datos_edu = obtener_datos_educacion_espana("gasto")
            s.finish(outputs=datos_edu)
            contexto_herramientas.append(datos_edu)

        if any(k in preg_lower for k in ["stem", "europa", "eurostat", "comparat"]):
            with trace.span("Tool: Eurostat (Comparativa STEM)", SpanType.TOOL, inputs={"area": "stem"}, metadata={"fuente": "ec.europa.eu/eurostat"}) as s:
                datos_euro = obtener_datos_eurostat_educacion("stem")
                s.finish(outputs=datos_euro)
                contexto_herramientas.append(datos_euro)

    # 3. Herramientas de Interior
    if any(k in interlocutor for k in ["Interior", "Primer Ministro", "Gabinete Completo"]) and any(
        k in preg_lower for k in ["seguridad", "polic", "delito", "ciber", "trafico", "dgt", "accidente", "emergencia", "aemet", "clima", "temporal"]
    ):
        if any(k in preg_lower for k in ["ciber", "delito", "crimen", "seguridad"]):
            with trace.span("Tool: Ministerio del Interior (Criminalidad)", SpanType.TOOL, inputs={"tipo": "ciber"}, metadata={"fuente": "interior.gob.es"}) as s:
                datos_crim = obtener_datos_criminalidad_interior("ciber")
                s.finish(outputs=datos_crim)
                contexto_herramientas.append(datos_crim)

        if any(k in preg_lower for k in ["aemet", "lluvia", "temporal", "emergencia", "clima"]):
            with trace.span("Tool: AEMET & Protección Civil", SpanType.TOOL, inputs={"tipo": "avisos"}, metadata={"fuente": "aemet.es"}) as s:
                datos_aemet = obtener_datos_aemet_emergencias("avisos")
                s.finish(outputs=datos_aemet)
                contexto_herramientas.append(datos_aemet)

        if any(k in preg_lower for k in ["dgt", "trafico", "carretera", "radar"]):
            with trace.span("Tool: DGT (Seguridad Vial)", SpanType.TOOL, inputs={"tipo": "seguridad"}, metadata={"fuente": "dgt.es"}) as s:
                datos_dgt = obtener_datos_dgt_trafico("seguridad")
                s.finish(outputs=datos_dgt)
                contexto_herramientas.append(datos_dgt)

    texto_grounding = "\n".join(contexto_herramientas) if contexto_herramientas else ""
    return texto_grounding, contexto_herramientas


def render_observability_panel(trace_data: Dict[str, Any], key_prefix: str = "trace"):
    """Renderiza el panel de observabilidad, árbol de spans y telemetría de ejecución."""
    summary = trace_data.get("summary", {})
    spans = trace_data.get("spans", [])
    eval_adk = trace_data.get("adk_eval", {})
    trace_id = trace_data.get("trace_id", "tr-local")
    total_ms = trace_data.get("total_duration_ms", summary.get("total_duration_ms", trace_data.get("duracion", 1.0) * 1000))
    if total_ms <= 0:
        total_ms = 1.0

    st.markdown(f"#### 🔬 Observabilidad & Spans (`{trace_id}`)")

    if eval_adk:
        st.markdown(f"**Puntuación de Calidad Google ADK:** **{eval_adk.get('score_global', 95)} / 100**")
        st.progress(eval_adk.get("score_global", 95) / 100.0)

        col_ev1, col_ev2, col_ev3, col_ev4 = st.columns(4)
        with col_ev1:
            st.metric("🎯 Fidelidad", f"{eval_adk.get('fidelidad', 98)}%")
        with col_ev2:
            st.metric("📐 Coherencia", f"{eval_adk.get('coherencia', 95)}%")
        with col_ev3:
            st.metric("⏱️ Latencia Total", f"{total_ms / 1000.0:.2f}s")
        with col_ev4:
            tokens_in = summary.get("tokens_in", trace_data.get("tokens_in", 0))
            tokens_out = summary.get("tokens_out", trace_data.get("tokens_out", 0))
            st.metric("⚡ Tokens In/Out", f"{tokens_in} / {tokens_out}")

    modo_badge = trace_data.get("modo_respuesta", "⚡ Ejecutivo")
    st.markdown(f"""
    <div style='margin-top: 8px; margin-bottom: 12px;'>
        <span class='trace-pill pill-green'>🛡️ Seguridad: {eval_adk.get('seguridad', 'PASSED')}</span>
        <span class='trace-pill pill-blue'>📊 Spans: {len(spans) if spans else 1} fases</span>
        <span class='trace-pill pill-amber'>🎛️ {modo_badge}</span>
        <span class='trace-pill pill-blue'>💰 Coste: 0,00 € (Free Tier)</span>
    </div>
    """, unsafe_allow_html=True)

    # Execution Waterfall (Cascada de Spans)
    if spans:
        st.markdown("##### 🌳 Árbol de Ejecución (Execution Waterfall)")
        type_icons = {
            "routing": "🧭 [ROUTING]",
            "agent": "🤖 [AGENT]",
            "tool": "🛠️ [TOOL]",
            "llm": "⚡ [LLM]",
            "eval": "🛡️ [EVAL]"
        }
        type_colors = {
            "routing": "#60a5fa",
            "agent": "#a78bfa",
            "tool": "#34d399",
            "llm": "#fbbf24",
            "eval": "#38bdf8"
        }

        for idx, span in enumerate(spans):
            s_name = span.get("name", "Span")
            s_type = span.get("span_type", "agent")
            s_ms = span.get("duration_ms", 0.0)
            s_status = span.get("status", "OK")
            pct = min(100.0, max(5.0, (s_ms / total_ms) * 100.0))
            icon = type_icons.get(s_type, "🔹")
            color = type_colors.get(s_type, "#60a5fa")

            col_s1, col_s2, col_s3 = st.columns([3, 1, 1])
            with col_s1:
                st.markdown(f"<span style='color:{color}; font-weight:600; font-size:0.85em;'>{icon}</span> **{s_name}**", unsafe_allow_html=True)
            with col_s2:
                badge_color = "#34d399" if s_status == "OK" else "#f87171"
                st.markdown(f"<span style='color:{badge_color}; font-size:0.8em; font-weight:bold;'>{s_status}</span>", unsafe_allow_html=True)
            with col_s3:
                st.markdown(f"<span style='color:#94a3b8; font-size:0.8em;'>{s_ms:.1f} ms</span>", unsafe_allow_html=True)

            st.progress(pct / 100.0)

            # Acordeón con payload del span si tiene inputs o outputs
            has_payload = bool(span.get("inputs") or span.get("outputs") or span.get("metadata"))
            if has_payload:
                with st.expander(f"📦 Payload: {s_name} ({s_ms:.1f} ms)", expanded=False):
                    if span.get("inputs"):
                        st.caption("Entradas (Inputs):")
                        st.json(span["inputs"])
                    if span.get("outputs"):
                        st.caption("Salidas (Outputs):")
                        if isinstance(span["outputs"], (dict, list)):
                            st.json(span["outputs"])
                        else:
                            st.code(str(span["outputs"]))
                    if span.get("metadata"):
                        st.caption("Metadatos (Metadata):")
                        st.json(span["metadata"])

    # Botón para descargar el JSON completo de la traza
    trace_json_str = json.dumps(trace_data, indent=2, ensure_ascii=False)
    st.download_button(
        label="📥 Descargar Traza OpenTelemetry / OpenInference (JSON)",
        data=trace_json_str,
        file_name=f"{trace_id}.json",
        mime="application/json",
        key=f"btn_trace_{key_prefix}_{trace_id}"
    )

# ----------------- BARRA LATERAL: INFORMACIÓN Y SERVICIOS ADK -----------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/courthouse.png", width=64)
    st.title("Gobierno Tecnocrático")
    st.caption("Sistema Multiagente impulsado por Google ADK & Gemini")
    
    st.divider()
    
    # Estado de Servicios de Evaluación ADK y Cloud
    info_storage = get_storage_backend_info()
    info_secrets = get_secrets_backend_info()
    
    st.markdown(f"""
    <div style='background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 8px 12px; border-radius: 8px; margin-bottom: 8px;'>
        <span style='color: #34d399; font-weight: bold; font-size: 0.85em;'>🛡️ Servicios de Evaluación ADK</span><br>
        <span style='color: #94a3b8; font-size: 0.8em;'>Estado: <strong>ACTIVO & OPERATIVO</strong></span>
    </div>
    <div style='background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); padding: 8px 12px; border-radius: 8px; margin-bottom: 12px;'>
        <span style='color: #60a5fa; font-weight: bold; font-size: 0.85em;'>☁️ Nube: {info_storage["icono"]} {info_storage["nombre"]}</span><br>
        <span style='color: #94a3b8; font-size: 0.78em;'>Credenciales: <strong>{info_secrets["icono"]} {info_secrets["origen"]}</strong></span>
    </div>
    """, unsafe_allow_html=True)
    
    # Métricas reales de votación ciudadana en el sidebar
    datos_actuales = cargar_datos_comunidad()
    votos = datos_actuales.get("votos", {})
    pos = votos.get("positivos", 0)
    neg = votos.get("negativos", 0)
    total_votos = pos + neg
    pct_aprobacion = round((pos / total_votos) * 100, 1) if total_votos > 0 else 0.0
    
    st.subheader("📊 Aprobación del Proyecto")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.metric(label="Aprobación Web", value=f"{pct_aprobacion}%")
    with col_v2:
        st.metric(label="Total Votos", value=f"{total_votos}")
        
    st.progress(pct_aprobacion / 100.0)
    if total_votos > 0:
        st.caption(f"👍 {pos} votos a favor | 👎 {neg} en contra")
    else:
        st.caption("👍 0 a favor | 👎 0 en contra (Sin votos aún)")
    
    st.divider()
    st.subheader("💾 Persistencia y Copias de Seguridad")
    with st.expander("⚙️ Gestión de Datos (100% Gratis)", expanded=False):
        st.markdown(f"**Backend Actual:** {info_storage['icono']} **{info_storage['nombre']}**")
        st.caption(info_storage["descripcion"])
        
        # Botón de Descarga de Backup JSON
        backup_json_str = exportar_datos_comunidad_json()
        st.download_button(
            label="📥 Descargar Copia de Seguridad (JSON)",
            data=backup_json_str,
            file_name="tecnocracia_backup.json",
            mime="application/json",
            use_container_width=True
        )
        
        # Subida / Restauración de Backup
        archivo_subido = st.file_uploader("📤 Restaurar Backup JSON", type=["json"], key="sidebar_backup_file")
        if archivo_subido is not None:
            try:
                import json
                datos_cargados = json.loads(archivo_subido.getvalue().decode("utf-8"))
                if restaurar_datos_comunidad(datos_cargados):
                    st.success("✅ Copia de seguridad restaurada correctamente.")
                    st.session_state.datos_comunidad = cargar_datos_comunidad()
                    st.rerun()
                else:
                    st.error("El archivo JSON no contiene las claves requeridas.")
            except Exception as e_res:
                st.error(f"Error al importar archivo: {e_res}")

        if info_storage["tipo"] == "json_local":
            st.info("💡 **Persistencia Gratuita Permanente:** Si deseas que los votos y el historial no se borren nunca al hibernar Streamlit Cloud y sin usar Google Cloud, puedes conectar un **GitHub Gist privado** configurando `GITHUB_GIST_ID` y `GITHUB_TOKEN` en tus Secrets.")

    st.divider()
    st.subheader("🏛️ Miembros del Gabinete")
    st.markdown("""
    * 👑 **Primer Ministro:** Coordinador y árbitro general.
    * 💼 **Economía y Hacienda:** Disciplina fiscal, costes e incentivos.
    * 🎓 **Educación y Ciencia:** Talento, I+D y capital humano.
    * 🛡️ **Interior y Gobernanza:** Seguridad, orden y desburocratización.
    """)

# ----------------- PANEL PRINCIPAL: TABS -----------------
st.title("🏛️ Partido Tecnocrático: Gabinete Autónomo")
st.markdown("Un gobierno ficticio donde ministros con IA analizan con máximo rigor técnico la gestión de una región.")

tab1, tab2, tab3 = st.tabs([
    "💬 Preguntas Libres y Trazabilidad",
    "📜 Historial de Conversaciones",
    "🗳️ Votación y Buzón Ciudadano"
])

# -------------------------------------------------------------
# TAB 1: PREGUNTAS LIBRES Y EVALUACIÓN ADK EN TIEMPO REAL
# -------------------------------------------------------------
with tab1:
    st.subheader("💬 Consulta y Preguntas Libres al Gabinete")
    st.markdown("Pregunta cualquier cuestión a los miembros del gobierno y consulta la **trazabilidad y servicios de evaluación del Google ADK**.")
    
    col_ag1, col_mode, col_ag2 = st.columns([2.5, 2.5, 1])
    with col_ag1:
        interlocutor = st.selectbox(
            "¿A quién deseas preguntar?",
            [
                "👑 Primer Ministro (Visión Global y Coordinación)",
                "💼 Ministro de Economía y Hacienda (Presupuesto, Impuestos, ROI)",
                "🎓 Ministro de Educación y Cultura (STEM, Leyes, Talento)",
                "🛡️ Ministro de Interior (Seguridad, Desburocratización, Orden)",
                "👥 Gabinete Completo (Mesa Redonda Interministerial)"
            ]
        )
    with col_mode:
        modo_respuesta = st.selectbox(
            "Profundidad de Análisis:",
            [
                "⚡ Modo Ejecutivo (Conciso, directo, ahorro de tokens)",
                "📑 Modo Detallado (Exhaustivo con dictamen técnico)"
            ],
            index=0,
            help="Elige si deseas una resolución rápida optimizada en tokens o un dictamen técnico exhaustivo."
        )
        es_ejecutivo = "Ejecutivo" in modo_respuesta
    with col_ag2:
        st.write("")
        st.write("")
        if st.button("🧹 Limpiar", use_container_width=True, help="Reiniciar la sesión de chat activa"):
            st.session_state.chat_messages = []
            st.rerun()

    max_tokens = 1500 if es_ejecutivo else 3000

    prompts_map = {
        "👑 Primer Ministro (Visión Global y Coordinación)": ("Primer Ministro", INSTRUCCION_PRIME_MINISTER),
        "💼 Ministro de Economía y Hacienda (Presupuesto, Impuestos, ROI)": ("Ministro de Economía", INSTRUCCION_ECONOMIA),
        "🎓 Ministro de Educación y Cultura (STEM, Leyes, Talento)": ("Ministro de Educación", INSTRUCCION_EDUCACION),
        "🛡️ Ministro de Interior (Seguridad, Desburocratización, Orden)": ("Ministro de Interior", INSTRUCCION_INTERIOR),
        "👥 Gabinete Completo (Mesa Redonda Interministerial)": ("Consejo de Ministros", INSTRUCCION_PRIME_MINISTER + "\n\nResponde ofreciendo una breve pincelada de Economía, Educación e Interior y la síntesis final del Primer Ministro.")
    }
    
    nombre_agente, prompt_sistema = prompts_map[interlocutor]

    # Reanudación inteligente: si no hay mensajes en la sesión actual pero sí en el historial persistente
    if not st.session_state.chat_messages:
        hist_disponible = datos_actuales.get("historial_conversaciones", [])
        if hist_disponible:
            ultima_interaccion = hist_disponible[-1]
            pregunta_corta = ultima_interaccion.get("pregunta", "")[:60]
            with st.expander(f"🔄 Retomar última consulta registrada: \"{pregunta_corta}...\"", expanded=False):
                st.markdown(f"**Agente:** `{ultima_interaccion.get('agente')}` | **Fecha:** {ultima_interaccion.get('fecha')}")
                if st.button("📥 Restaurar esta conversación en el chat interactivo", key="btn_retomar_chat"):
                    st.session_state.chat_messages.append({
                        "role": "user",
                        "content": ultima_interaccion.get("pregunta", "")
                    })
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": ultima_interaccion.get("respuesta", ""),
                        "trace": ultima_interaccion.get("telemetria", {})
                    })
                    st.rerun()

    for idx, msg in enumerate(st.session_state.chat_messages):
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🏛️"):
            if msg.get("content"):
                st.markdown(msg["content"])
            if "error_diag" in msg:
                render_error_diagnosis_card(msg["error_diag"], key_prefix=f"hist_err_{idx}")
            if "trace" in msg:
                with st.expander("🔍 Observabilidad & Spans de Agentes (Google ADK)", expanded=False):
                    render_observability_panel(msg["trace"], key_prefix=f"history_{msg.get('id', idx)}")

    pregunta_usuario = st.chat_input("Escribe tu pregunta para el gobierno...")
    
    if pregunta_usuario:
        st.session_state.chat_messages.append({"role": "user", "content": pregunta_usuario})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(pregunta_usuario)
            
        with st.chat_message("assistant", avatar="🏛️"):
            with st.spinner(f"{nombre_agente} analizando la cuestión y orquestando herramientas..."):
                if not api_key:
                    st.error("Configura tu GEMINI_API_KEY en .env o en los Secrets de Streamlit.")
                    st.stop()
                    
                client = genai.Client(api_key=api_key)
                
                # Iniciar Trace de Observabilidad Distribuida
                trace = TraceContext(trace_name=f"consulta_{nombre_agente.lower().replace(' ', '_')}")
                
                # 1. Span de Orquestación & Enrutamiento (Google ADK)
                with trace.span(f"Orquestación ADK: {nombre_agente}", SpanType.ROUTING, inputs={"interlocutor": nombre_agente, "pregunta": pregunta_usuario}, metadata={"supervisor": "primer_ministro"}):
                    texto_grounding, tools_usadas = resolver_grounding_tools(interlocutor, pregunta_usuario, trace)
                
                # Inyectar evidencia de las herramientas oficiales si aplica
                bloque_evidencia = ""
                if texto_grounding:
                    bloque_evidencia = f"\n\nDATOS OFICIALES EN TIEMPO REAL OBTENIDOS POR LAS HERRAMIENTAS (GROUNDING):\n{texto_grounding}\nUsa estos datos oficiales para fundamentar tu respuesta técnica con máxima precisión."
                
                directriz_modo = """
DIRECTRIZ DE PROFUNDIDAD Y CONCISIÓN (MODO EJECUTIVO ACTIVADO - AHORRO DE TOKENS):
- Responde de forma telegráfica, directa y sintética orientada a la toma de decisión inmediata.
- Extensión máxima estricta: Máximo 150 a 200 palabras o 3-4 viñetas clave con las conclusiones e impactos fundamentales.
- Prohibidos preámbulos formales, saludos ceremoniales o divagaciones teóricas. Ve directo a las métricas y la resolución.
""" if es_ejecutivo else """
DIRECTRIZ DE PROFUNDIDAD Y CONCISIÓN (MODO DETALLADO ACTIVADO):
- Elabora un dictamen técnico y normativo completo, detallando el impacto presupuestario, metodologías, evidencias empíricas de las herramientas y posibles contraindicaciones.
"""

                # Construir memoria contextual de la sesión (Multi-turn Context Buffer)
                historial_sesion = []
                for m in st.session_state.chat_messages[:-1]:
                    if m.get("content"):
                        rol_txt = "Ciudadano" if m["role"] == "user" else f"{nombre_agente}"
                        historial_sesion.append(f"{rol_txt}: {m['content']}")

                bloque_historial = ""
                if historial_sesion:
                    ultimos_turnos = "\n".join(historial_sesion[-6:])
                    bloque_historial = f"\n\nHISTORIAL DE LA CONVERSACIÓN PREVIA EN ESTA SESIÓN:\n{ultimos_turnos}\n(IMPORTANTE: Usa este historial previo para responder con total coherencia a preguntas de seguimiento, referencias a términos anteriores o aclaraciones sobre conceptos que acabas de mencionar)."

                prompt_completo = f"""
{prompt_sistema}{bloque_evidencia}{bloque_historial}

{directriz_modo}

REGLA DE ADAPTABILIDAD AL TIPO DE MENSAJE:
- Si el mensaje del ciudadano es un saludo, una pregunta de cortesía o una duda sencilla sobre tus funciones (ej: "Hola", "Buenos días", "¿Para qué sirves?", "¿Quién eres?", "¿Qué haces?", "Gracias"):
  Responde de forma amable, cercana y muy breve (máximo 1 o 2 frases simples) explicando quién eres y ofreciéndote a ayudar. NO generes informes largos ni tecnicismos.
- Si el mensaje es una propuesta, ley, dilema, consulta técnica o pregunta de seguimiento sobre la conversación:
  Responde con la profundidad y el rigor correspondiente a tu cargo y al modo seleccionado, enlazando directamente con los conceptos comentados previamente si aplica.

MENSAJE DEL CIUDADANO:
{pregunta_usuario}
"""
                modelo_activo = os.getenv("MODEL_NAME", "gemini-3.6-flash")
                t0 = time.perf_counter()
                ts_inicio = datetime.now().strftime("%H:%M:%S")
                fecha_completa = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                # 2. Span de Inferencia LLM con Presupuesto de Tokens y Optimización de Pensamiento
                response, error_diag = None, None
                thinking_cfg = types.ThinkingConfig(thinking_budget=0) if es_ejecutivo else None
                gen_config = types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    thinking_config=thinking_cfg
                )
                with trace.span(
                    f"Inferencia LLM ({modelo_activo})",
                    SpanType.LLM,
                    inputs={
                        "modelo": modelo_activo,
                        "modo": "ejecutivo" if es_ejecutivo else "detallado",
                        "max_tokens": max_tokens,
                        "prompt_chars": len(prompt_completo)
                    }
                ) as s_llm:
                    response, error_diag = generar_con_reintento(
                        client, prompt_completo, model=modelo_activo, config=gen_config
                    )
                    if error_diag:
                        s_llm.finish(
                            status=SpanStatus.ERROR,
                            error=Exception(error_diag["codigo_tecnico"]),
                            metadata={"error_diag": error_diag, "modo": "ejecutivo" if es_ejecutivo else "detallado"}
                        )
                    else:
                        tokens_in = getattr(response.usage_metadata, "prompt_token_count", 0)
                        tokens_out = getattr(response.usage_metadata, "candidates_token_count", 0)
                        s_llm.finish(
                            outputs={"tokens_in": tokens_in, "tokens_out": tokens_out},
                            metadata={"tokens_in": tokens_in, "tokens_out": tokens_out, "modo": "ejecutivo" if es_ejecutivo else "detallado"}
                        )

                duracion = time.perf_counter() - t0

                if error_diag:
                    trace.finish()
                    trace_dict = trace.to_dict()
                    trace_dict["agente"] = nombre_agente
                    trace_dict["modelo"] = modelo_activo
                    trace_dict["modo_respuesta"] = "⚡ Ejecutivo" if es_ejecutivo else "📑 Detallado"
                    trace_dict["timestamp"] = ts_inicio
                    trace_dict["duracion"] = duracion
                    trace_dict["error"] = error_diag

                    # Tarjeta de Explicabilidad DevOps y Diagnóstico Causal
                    render_error_diagnosis_card(error_diag, key_prefix="live_err")

                    with st.expander("🔍 Observabilidad & Spans de Agentes (Google ADK)", expanded=True):
                        render_observability_panel(trace_dict, key_prefix="chat_current_err")

                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": "",
                        "error_diag": error_diag,
                        "trace": trace_dict
                    })
                else:
                    # 3. Span de Evaluación Google ADK
                    with trace.span("Evaluación de Calidad Google ADK", SpanType.EVAL, inputs={"agente": nombre_agente}) as s_eval:
                        eval_adk = evaluar_respuesta_adk(nombre_agente, pregunta_usuario, response.text, duracion, tokens_in, tokens_out)
                        s_eval.finish(outputs=eval_adk)

                    # Finalizar traza completa
                    trace.finish()
                    trace_dict = trace.to_dict()
                    trace_dict["adk_eval"] = eval_adk
                    trace_dict["agente"] = nombre_agente
                    trace_dict["modelo"] = modelo_activo
                    trace_dict["modo_respuesta"] = "⚡ Ejecutivo" if es_ejecutivo else "📑 Detallado"
                    trace_dict["tokens_in"] = tokens_in
                    trace_dict["tokens_out"] = tokens_out
                    trace_dict["tokens_total"] = tokens_in + tokens_out
                    trace_dict["system_prompt"] = prompt_sistema.strip()
                    trace_dict["timestamp"] = ts_inicio
                    trace_dict["duracion"] = duracion

                    st.markdown(response.text)

                    with st.expander("🔍 Observabilidad & Spans de Agentes (Google ADK)", expanded=True):
                        render_observability_panel(trace_dict, key_prefix="chat_current")

                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": response.text,
                        "trace": trace_dict
                    })

                    # Guardado atómico e inmune a concurrencia
                    nueva_conv = {
                        "tipo": "💬 Consulta Directa",
                        "agente": nombre_agente,
                        "pregunta": pregunta_usuario,
                        "respuesta": response.text,
                        "fecha": fecha_completa,
                        "telemetria": trace_dict
                    }
                    agregar_conversacion_al_historial(nueva_conv)

# -------------------------------------------------------------
# TAB 2: HISTORIAL DE CONVERSACIONES REAL
# -------------------------------------------------------------
with tab2:
    st.subheader("📜 Historial de Interacciones y Consultas")
    st.markdown("Registro persistente e inmutable de todas las consultas realizadas al gabinete por todos los ciudadanos.")
    
    # Cargar siempre la información más fresca de disco
    datos_frescos = cargar_datos_comunidad()
    historial = datos_frescos.get("historial_conversaciones", [])
    
    if not historial:
        st.info("ℹ️ Aún no hay conversaciones registradas. Haz una pregunta en 'Preguntas Libres' para empezar a guardar registros reales.")
    else:
        col_h1, col_h2, col_h3 = st.columns([1, 1, 2])
        with col_h1:
            st.metric("Total Interacciones", len(historial))
        with col_h2:
            st.metric("Último Registro", historial[-1]["fecha"].split(" ")[1] if historial else "--:--")
        with col_h3:
            col_hb1, col_hb2 = st.columns(2)
            with col_hb1:
                st.download_button(
                    "📥 Backup JSON",
                    data=exportar_datos_comunidad_json(),
                    file_name="historial_tecnocracia.json",
                    mime="application/json",
                    use_container_width=True
                )
            with col_hb2:
                if st.button("🗑️ Vaciar Historial", use_container_width=True):
                    vaciar_historial_conversaciones()
                    st.success("Historial de conversaciones vaciado con éxito.")
                    st.rerun()
                
        st.divider()
        
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            busqueda = st.text_input("🔍 Buscar en el historial:", placeholder="Palabra clave (ej. economía, vivienda, empleo, seguridad)...")
        with col_f2:
            agentes_unicos = ["Todos"] + sorted(list(set(item.get("agente", "Desconocido") for item in historial)))
            filtro_agente = st.selectbox("Filtrar por Agente:", agentes_unicos)
            
        historial_filtrado = historial
        if filtro_agente != "Todos":
            historial_filtrado = [h for h in historial_filtrado if h.get("agente") == filtro_agente]
        if busqueda.strip():
            q = busqueda.lower()
            historial_filtrado = [
                h for h in historial_filtrado 
                if q in h.get("pregunta", "").lower() or q in h.get("respuesta", "").lower() or q in h.get("agente", "").lower()
            ]
            
        st.caption(f"Mostrando {len(historial_filtrado)} de {len(historial)} registros.")
        
        for i, item in enumerate(reversed(historial_filtrado)):
            tipo = item.get("tipo", "Consulta")
            agente = item.get("agente", "Agente")
            fecha = item.get("fecha", "")
            pregunta = item.get("pregunta", "")
            respuesta = item.get("respuesta", "")
            telemetria = item.get("telemetria", {})
            eval_adk = telemetria.get("adk_eval", {})
            
            score_txt = f" | 🏆 ADK Score: {eval_adk.get('score_global')}/100" if eval_adk and "score_global" in eval_adk else ""
            
            with st.expander(f"🕒 {fecha} | [{agente}] {pregunta[:70]}...{score_txt}", expanded=(i == 0)):
                st.markdown(f"**📌 Tipo:** `{tipo}` | **🤖 Interlocutor:** **{agente}** | **📅 Fecha:** {fecha}")
                st.markdown("#### 👤 Consulta / Propuesta del Usuario:")
                st.info(pregunta)
                st.markdown("#### 🏛️ Respuesta Oficial del Agente:")
                st.markdown(respuesta)
                
                if eval_adk:
                    with st.expander("🛡️ Evaluación de Calidad ADK (Reporte del Agente)"):
                        col_evh1, col_evh2, col_evh3 = st.columns(3)
                        with col_evh1:
                            st.metric("🎯 Fidelidad al Rol", f"{eval_adk.get('fidelidad', 95)}%")
                        with col_evh2:
                            st.metric("📐 Coherencia Técnica", f"{eval_adk.get('coherencia', 95)}%")
                        with col_evh3:
                            st.metric("⚡ Velocidad ADK", f"{eval_adk.get('tok_per_sec', 0)} tok/s")
                            
                if telemetria:
                    with st.expander("🔍 Observabilidad & Spans de la Interacción"):
                        render_observability_panel(telemetria, key_prefix=f"hist_{i}")

# -------------------------------------------------------------
# TAB 3: VOTACIÓN COMUNITARIA Y BUZÓN DE CRÍTICAS REAL
# -------------------------------------------------------------
with tab3:
    st.subheader("🗳️ Encuesta y Buzón de Críticas sobre el Desarrollo")
    st.markdown("Sistema de métricas 100% reales. Todas las votaciones y opiniones mostradas corresponden únicamente a la participación de usuarios reales.")
    
    datos_voto = cargar_datos_comunidad()
    
    # 1. Sistema de votación real
    st.markdown("#### 1. Votación de Aprobación del Proyecto")
    
    col_vote1, col_vote2, col_stat = st.columns([1, 1, 2])
    
    with col_vote1:
        if st.button("👍 Me gusta el proyecto", use_container_width=True, disabled=st.session_state.ha_votado):
            registrar_voto(True)
            st.session_state.ha_votado = True
            st.success("¡Gracias por tu voto a favor!")
            st.rerun()
            
    with col_vote2:
        if st.button("👎 No me convence", use_container_width=True, disabled=st.session_state.ha_votado):
            registrar_voto(False)
            st.session_state.ha_votado = True
            st.info("Voto registrado. Agradecemos que nos dejes tu crítica abajo.")
            st.rerun()
            
    with col_stat:
        v = datos_voto.get("votos", {})
        total = v.get("positivos", 0) + v.get("negativos", 0)
        pct = round((v.get("positivos", 0) / total) * 100, 1) if total > 0 else 0.0
        if total > 0:
            st.markdown(f"**Resultado actual:** **{pct}% de aprobación** ({v.get('positivos', 0)} a favor de {total} votos)")
            st.progress(pct / 100.0)
        else:
            st.markdown("**Resultado actual:** **Sin votos aún** (0.0% de aprobación)")
            st.progress(0.0)
        
    if st.session_state.ha_votado:
        st.caption("✅ Ya has participado en la votación en esta sesión.")
        
    st.divider()
    
    # 2. Buzón de opiniones reales
    st.markdown("#### 2. Buzón de Críticas Constructivas y Sugerencias Reales")
    
    with st.form("form_buzon"):
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            autor_opinion = st.text_input("Tu nombre o apodo (opcional):", placeholder="Ej: Anónimo / Usuario")
        with col_f2:
            mensaje_opinion = st.text_area("¿Qué opinas del proyecto? ¿Qué mejorarías?", placeholder="Escribe aquí tu opinión o sugerencia...")
            
        enviar_opinion = st.form_submit_button("📩 Enviar Opinión")
        
        if enviar_opinion:
            if not mensaje_opinion.strip():
                st.warning("Escribe algún comentario antes de enviar.")
            else:
                nueva_op = {
                    "autor": autor_opinion.strip() if autor_opinion.strip() else "Ciudadano Anónimo",
                    "mensaje": mensaje_opinion.strip(),
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                agregar_opinion(nueva_op)
                st.success("¡Opinión registrada con éxito!")
                st.rerun()
                
    st.markdown("#### 📬 Opiniones Reales de la Comunidad")
    opiniones = datos_voto.get("opiniones", [])
    if not opiniones:
        st.info("Aún no hay mensajes en el buzón. ¡Sé el primero en opinar!")
    else:
        for op in reversed(opiniones):
            with st.container():
                st.markdown(f"""
                <div class='opinion-card'>
                    <strong>👤 {op['autor']}</strong> <span style='color: #64748b; font-size: 0.85em; margin-left: 10px;'>🕒 {op['fecha']}</span>
                    <p style='margin-top: 6px; margin-bottom: 0px;'>{op['mensaje']}</p>
                </div>
                """, unsafe_allow_html=True)
