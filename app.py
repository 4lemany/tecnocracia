"""
🏛️ Tecnocracia: Plataforma de Gobierno Multiagente con Google ADK y Gemini.
Chat Libre con Trazabilidad, Evaluación ADK, Historial de Conversaciones, Votación Comunitaria y Buzón de Opiniones Real.
"""

import os
import sys
import json
import time
import threading
from typing import Any, Optional, Dict, List
from datetime import datetime
from pathlib import Path
import streamlit as st

# Configuración de página adaptada para móvil y escritorio (solo en ejecución de Streamlit)
if "pytest" not in sys.modules and "unittest" not in sys.modules:
    st.set_page_config(
        page_title="Partido Tecnocrático de España | Gobernanza con IA",
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
from services.secrets_manager import (
    get_gemini_api_key,
    get_secondary_gemini_api_key,
    get_groq_api_key,
    get_secrets_backend_info
)
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
    restaurar_datos_comunidad,
    obtener_metricas_cuota_gemini,
    obtener_hora_espana
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

# =====================================================================
# CLASES Y CONECTORES MULTI-PROVEEDOR (GROQ LPU / GEMINI MULTI-KEY)
# =====================================================================
class GroqUsageMetadata:
    def __init__(self, prompt_tokens: int, candidates_tokens: int):
        self.prompt_token_count = prompt_tokens
        self.candidates_token_count = candidates_tokens


class GroqResponseWrapper:
    def __init__(self, text: str, prompt_tokens: int, candidates_tokens: int, model: str = "llama-3.3-70b-versatile", failover: bool = False):
        self.text = text
        self.provider = "groq"
        self.model = model
        self.es_failover = failover
        self.usage_metadata = GroqUsageMetadata(prompt_tokens, candidates_tokens)


def generar_con_groq(prompt_texto: str, groq_key: str, model: str = "llama-3.3-70b-versatile", max_tokens: int = 1500, failover: bool = False) -> tuple[Any, Optional[dict]]:
    """
    Inferencia gratuita en Groq Cloud utilizando arquitectura LPU ultra-rápida.
    Ofrece 30 RPM y 14.400 peticiones diarias gratuitas (0,00 €) sin tarjeta de crédito.
    """
    import requests
    if not groq_key or not groq_key.strip():
        return None, diagnosticar_error_gemini(Exception("API_KEY_INVALID: Groq API Key no configurada."))

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt_texto}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.4
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            t_in = usage.get("prompt_tokens", 0)
            t_out = usage.get("completion_tokens", 0)
            return GroqResponseWrapper(content, t_in, t_out, model=model, failover=failover), None
        else:
            try:
                err_data = resp.json()
                msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                msg = resp.text
            return None, diagnosticar_error_gemini(Exception(f"Groq API Error {resp.status_code}: {msg}"))
    except Exception as e:
        return None, diagnosticar_error_gemini(e)


# Función de llamada a Gemini con manejo robusto de reintentos, degradación elegante y observabilidad
def generar_con_reintento(
    client,
    contents,
    model="gemini-3.6-flash",
    config=None,
    max_intentos=3,
    groq_key=None,
    gemini_key_2=None,
    proveedor_preferido="auto",
    max_tokens=1500
):
    """
    Invoca a Google Gemini o Groq con política de reintentos, failover automático y observabilidad:
    1. Si el usuario selecciona Groq de forma prioritaria, ejecuta Groq LPU (Llama 3.3 70B).
    2. Si usa Gemini (o modo Auto): ejecuta Gemini con backoff.
    3. Si Gemini devuelve 429 RESOURCE_EXHAUSTED (15 RPM) o 503 UNAVAILABLE:
       - Si existe gemini_key_2: conmuta a la clave secundaria de Gemini.
       - Si existe groq_key: failover transparente a Groq Cloud sin interrumpir al usuario.
       - Si no hay claves secundarias: pausa con backoff exponencial.
    """
    # Preferencia explícita por Groq
    if proveedor_preferido == "groq" and groq_key:
        resp_groq, err_groq = generar_con_groq(contents, groq_key, max_tokens=max_tokens, failover=False)
        if resp_groq:
            return resp_groq, None
        if client:
            st.toast("⚠️ Groq temporalmente indispuesto. Conmutando a Google Gemini...", icon="🔄")
        else:
            return None, err_groq

    ultimo_error = None
    backoff_tiempos = [2, 4]

    for intento in range(max_intentos):
        try:
            if not client:
                raise Exception("API_KEY_INVALID: GEMINI_API_KEY no configurada.")

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
            es_rate_limit = any(k in err_msg for k in ["429", "RESOURCE_EXHAUSTED", "quota", "QuotaExceeded"])
            es_sobrecarga = any(k in err_msg for k in ["ServerError", "500", "503", "504", "overloaded", "UNAVAILABLE"])
            es_transitorio = es_rate_limit or es_sobrecarga

            # Failover Nivel 1: Clave Secundaria de Gemini si es 429 / 503
            if es_transitorio and gemini_key_2:
                try:
                    st.toast("🔄 Gemini Clave 1 saturada (15 RPM). Saltando a Gemini Clave 2...", icon="⚡")
                    client_sec = genai.Client(api_key=gemini_key_2)
                    if config is not None:
                        resp_sec = client_sec.models.generate_content(model=model, contents=contents, config=config)
                    else:
                        resp_sec = client_sec.models.generate_content(model=model, contents=contents)
                    if getattr(resp_sec, "text", None):
                        return resp_sec, None
                except Exception as e_sec:
                    ultimo_error = e_sec

            # Failover Nivel 2: Groq LPU Automático e Instantáneo (30 RPM, 0€)
            if es_transitorio and groq_key:
                st.toast("🚀 Límite de Gemini alcanzado. Conmutando a Groq LPU (Llama 3.3 70B)...", icon="🚀")
                resp_groq, err_groq = generar_con_groq(contents, groq_key, max_tokens=max_tokens, failover=True)
                if resp_groq:
                    return resp_groq, None
                else:
                    ultimo_error = Exception(f"Gemini y Groq agotados: {err_groq.get('detalle_tecnico', '')}")

            if es_transitorio and intento < max_intentos - 1:
                if es_rate_limit:
                    espera = 6 if intento == 0 else 10
                else:
                    espera = backoff_tiempos[intento] if intento < len(backoff_tiempos) else 4
                st.toast(f"⏳ Servidores con alta demanda. Reintentando automáticamente ({intento+1}/{max_intentos})...", icon="⏳")
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


def cb_reiniciar_chat():
    """Callback atómico para vaciar la conversación en 1 solo clic."""
    st.session_state.chat_messages = []
    st.session_state.pregunta_reintento = None


def cb_reintentar_consulta():
    """Callback atómico para reintentar la última pregunta del usuario en 1 solo clic."""
    pregunta_guardada = None
    for m in reversed(st.session_state.get("chat_messages", [])):
        if m.get("role") == "user" and m.get("content"):
            pregunta_guardada = m["content"]
            break
    
    if pregunta_guardada:
        st.session_state.pregunta_reintento = pregunta_guardada
        # Eliminar el turno de error anterior para reejecutar limpiamente
        if st.session_state.get("chat_messages") and "error_diag" in st.session_state.chat_messages[-1]:
            st.session_state.chat_messages.pop()


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

    # Opción instantánea de vincular Groq gratis si es 429
    if error_diag.get("categoria") == "CUOTA_EXCEDIDA" and not get_groq_api_key():
        with st.expander("🚀 ¿Cómo evitar este límite de 15 peticiones/minuto de forma 100% gratuita?", expanded=True):
            st.markdown("""
            **La API de Groq Cloud es completamente gratuita y ofrece 30 peticiones/minuto (el doble) y 14.400 peticiones/día:**
            1. Consigue tu API Key en 20 segundos en [console.groq.com/keys](https://console.groq.com/keys) *(No requiere tarjeta de crédito ni datos de pago)*.
            2. Pégala abajo y pulsa **Vincular Groq y Reintentar**:
            """)
            col_k1, col_k2 = st.columns([3, 1.5])
            with col_k1:
                input_groq = st.text_input(
                    "Introduce tu GROQ_API_KEY (ej: gsk_...)",
                    type="password",
                    key=f"groq_input_{key_prefix}",
                    help="Tu clave se guardará en tu sesión activa y se usará para failover automático inmediato."
                )
            with col_k2:
                st.write("")
                st.write("")
                if st.button("🚀 Vincular y Reintentar", key=f"btn_save_groq_{key_prefix}", type="primary", use_container_width=True):
                    if input_groq and input_groq.strip():
                        st.session_state.custom_groq_api_key = input_groq.strip()
                        st.session_state.motor_ia_preferido = "Groq Cloud (LPU Llama 3.3 70B - 30 RPM Gratuito)"
                        cb_reintentar_consulta()
                        st.rerun()
                    else:
                        st.warning("Introduce una clave válida.")

    # Botones directos de reintento y reinicio en 1 clic mediante callbacks atómicos
    col_reintento, col_reiniciar = st.columns([1.5, 1.5])
    with col_reintento:
        st.button(
            "🔄 Reintentar Consulta",
            key=f"btn_retry_{key_prefix}",
            type="primary",
            use_container_width=True,
            on_click=cb_reintentar_consulta
        )
    with col_reiniciar:
        st.button(
            "🧹 Reiniciar Conversación",
            key=f"btn_reset_{key_prefix}",
            use_container_width=True,
            on_click=cb_reiniciar_chat,
            help="Vaciar la conversación y volver a empezar de cero"
        )

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
    cuota_fast = obtener_metricas_cuota_gemini()
    st.markdown(f"""
    <div style='margin-top: 8px; margin-bottom: 12px;'>
        <span class='trace-pill pill-green'>🛡️ Seguridad: {eval_adk.get('seguridad', 'PASSED')}</span>
        <span class='trace-pill pill-blue'>📊 Spans: {len(spans) if spans else 1} fases</span>
        <span class='trace-pill pill-amber'>🎛️ {modo_badge}</span>
        <span class='trace-pill pill-blue'>⚡ Cuota: {cuota_fast['peticiones_restantes']} rest. (Recarga en {cuota_fast['tiempo_restante_reset']})</span>
        <span class='trace-pill pill-green'>💰 Coste: 0,00 € (Free Tier)</span>
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
    st.title("Partido Tecnocrático")
    st.caption("Propuesta de Gobernanza para España (Google ADK & Gemini)")
    
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

    # Métricas de consumo y cuota de la API de Gemini (Free Tier)
    cuota_api = obtener_metricas_cuota_gemini(datos_actuales)
    st.subheader("⚡ Cuota y Consumo API Gemini")
    
    st.markdown(f"""
    <div style='background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 10px 12px; margin-bottom: 10px;'>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span style='font-size: 0.82rem; font-weight: 700; color: #0284c7;'>ESTADO: {cuota_api["estado"]}</span>
            <span style='font-size: 0.75rem; color: #64748b; font-weight: 600;'>Free Tier</span>
        </div>
        <div style='font-size: 0.78rem; color: #475569; margin-top: 4px;'>
            🔄 <strong>Se recarga en:</strong> <span style='color: #0369a1; font-weight: 700;'>{cuota_api["tiempo_restante_reset"]}</span> (00:00 UTC)
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_cq1, col_cq2 = st.columns(2)
    with col_cq1:
        st.metric(label="Peticiones Hoy", value=f"{cuota_api['peticiones_hoy']} / {cuota_api['limite_rpd']}")
    with col_cq2:
        st.metric(label="Restantes Hoy", value=f"{cuota_api['peticiones_restantes']}")

    st.progress(min(1.0, cuota_api["pct_diario"] / 100.0))
    st.caption(f"⚡ **Ritmo:** {cuota_api['rpm_actual']} / {cuota_api['limite_rpm']} req/min | 🪙 **Tokens hoy:** {cuota_api['tokens_hoy']:,} | 💰 **Coste:** 0,00 €")
    
    # Configuración de Redundancia y Alternativas Gratuitas (Groq / Multi-Key)
    with st.expander("🛡️ Redundancia & Failover Gratuito (Groq / Clave 2)", expanded=False):
        st.markdown("**Evita el límite de 15 RPM sin pagar nada:**")
        motor_opciones = [
            "⚡ Auto / Híbrido (Gemini con Failover a Groq)",
            "🚀 Groq Cloud (LPU Llama 3.3 70B - 30 RPM)",
            "💎 Google Gemini (gemini-3.6-flash)"
        ]
        idx_default = 0
        motor_actual_sesion = st.session_state.get("motor_ia_preferido", "")
        if "Groq" in motor_actual_sesion and "Auto" not in motor_actual_sesion:
            idx_default = 1
        elif "Gemini" in motor_actual_sesion and "Auto" not in motor_actual_sesion:
            idx_default = 2

        motor_sel = st.selectbox(
            "Motor preferido:",
            motor_opciones,
            index=idx_default,
            key="sb_motor_ia_select"
        )
        st.session_state.motor_ia_preferido = motor_sel

        groq_actual = get_groq_api_key()
        estado_groq = "🟢 Vinculada" if groq_actual else "⚪ No configurada"
        st.markdown(f"**Groq LPU (30 RPM):** `{estado_groq}`")
        if not groq_actual:
            st.caption("Obtén tu clave gratis en [console.groq.com/keys](https://console.groq.com/keys) (Sin tarjeta).")
            nueva_groq = st.text_input("Vincular GROQ_API_KEY:", type="password", key="sb_groq_key_input")
            if st.button("Guardar Clave Groq", key="sb_btn_groq", use_container_width=True):
                if nueva_groq and nueva_groq.strip():
                    st.session_state.custom_groq_api_key = nueva_groq.strip()
                    st.success("✅ Clave Groq guardada para esta sesión.")
                    st.rerun()

        gemini_2_actual = get_secondary_gemini_api_key()
        estado_gem2 = "🟢 Vinculada" if gemini_2_actual else "⚪ No configurada"
        st.markdown(f"**Gemini Secundario:** `{estado_gem2}`")
        if not gemini_2_actual:
            st.caption("Segunda clave gratis de [Google AI Studio](https://aistudio.google.com/app/apikey).")
            nueva_gem2 = st.text_input("Vincular GEMINI_API_KEY_2:", type="password", key="sb_gem2_key_input")
            if st.button("Guardar Gemini 2", key="sb_btn_gem2", use_container_width=True):
                if nueva_gem2 and nueva_gem2.strip():
                    st.session_state.custom_gemini_api_key_2 = nueva_gem2.strip()
                    st.success("✅ Clave secundaria de Gemini guardada.")
                    st.rerun()

    st.divider()
    
    # Cálculo de métricas de votación
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
    st.subheader("🏛️ Consejo Técnico para España")
    st.markdown("""
    * 👑 **Primer Ministro:** Coordinación de Estado y visión estratégica nacional.
    * 💼 **Economía y Hacienda:** Productividad, reforma fiscal, deuda y pensiones.
    * 🎓 **Educación y FP:** Pacto por el talento, STEM, FP Dual y universidades.
    * 🛡️ **Interior y Gobernanza:** Ciberseguridad, modernización del Estado y mérito.
    """)

# ----------------- PANEL PRINCIPAL: TABS -----------------
st.title("🏛️ Partido Tecnocrático de España: Gabinete de Gobernanza")
st.markdown("Propuesta política y técnica para la gobernanza de España: decisiones públicas fundamentadas en datos oficiales, evidencia empírica y optimización matemática de los recursos del Estado.")

tab1, tab2, tab3 = st.tabs([
    "💬 Preguntas Libres y Trazabilidad",
    "📜 Historial de Conversaciones",
    "🗳️ Votación y Buzón Ciudadano"
])

# -------------------------------------------------------------
# TAB 1: PREGUNTAS LIBRES Y EVALUACIÓN ADK EN TIEMPO REAL
# -------------------------------------------------------------
with tab1:
    st.subheader("💬 Consulta a los Ministros Técnicos de España")
    st.markdown("Plantea cualquier cuestión, consulta o propuesta sobre la gobernanza de España y evalúa la **trazabilidad y rigor técnico del Google ADK**.")
    
    col_ag1, col_mode, col_ag2 = st.columns([2.5, 2.5, 1])
    with col_ag1:
        interlocutor = st.selectbox(
            "¿A qué responsable deseas consultar?",
            [
                "👑 Primer Ministro (Visión de Estado y Coordinación)",
                "💼 Ministro de Economía y Hacienda (Presupuesto, Deuda, Pensiones)",
                "🎓 Ministro de Educación y FP (Pacto de Estado, STEM, FP Dual)",
                "🛡️ Ministro de Interior (Seguridad, Ciberseguridad, Eficiencia)",
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
        st.button(
            "🧹 Reiniciar Conversación",
            use_container_width=True,
            help="Reiniciar la sesión de chat activa y limpiar la pantalla",
            on_click=cb_reiniciar_chat
        )

    max_tokens = 1500 if es_ejecutivo else 3000

    prompts_map = {
        "👑 Primer Ministro (Visión de Estado y Coordinación)": ("Primer Ministro", INSTRUCCION_PRIME_MINISTER),
        "💼 Ministro de Economía y Hacienda (Presupuesto, Deuda, Pensiones)": ("Ministro de Economía", INSTRUCCION_ECONOMIA),
        "🎓 Ministro de Educación y FP (Pacto de Estado, STEM, FP Dual)": ("Ministro de Educación", INSTRUCCION_EDUCACION),
        "🛡️ Ministro de Interior (Seguridad, Ciberseguridad, Eficiencia)": ("Ministro de Interior", INSTRUCCION_INTERIOR),
        "👥 Gabinete Completo (Mesa Redonda Interministerial)": ("Consejo de Ministros", INSTRUCCION_PRIME_MINISTER + "\n\nResponde ofreciendo una perspectiva técnica de Economía, Educación e Interior para España y la síntesis estratégica del Primer Ministro.")
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
            if msg.get("es_failover"):
                st.caption("🚀 *Respuesta servida mediante failover automático a Groq LPU (Llama 3.3 70B)*")
            elif msg.get("provider") == "groq":
                st.caption("🚀 *Inferencia Groq Cloud LPU (Llama 3.3 70B)*")
            if msg.get("content"):
                st.markdown(msg["content"])
            if "error_diag" in msg:
                err_id = msg.get("id", f"err_{idx}")
                render_error_diagnosis_card(msg["error_diag"], key_prefix=err_id)
            if "trace" in msg:
                with st.expander("🔍 Observabilidad & Spans de Agentes (Google ADK)", expanded=False):
                    render_observability_panel(msg["trace"], key_prefix=f"history_{msg.get('id', idx)}")

    pregunta_input = st.chat_input("Escribe tu consulta o propuesta para el gabinete de España...")
    pregunta_reintento = st.session_state.pop("pregunta_reintento", None)
    pregunta_usuario = pregunta_input or pregunta_reintento
    
    if pregunta_usuario:
        if not st.session_state.chat_messages or st.session_state.chat_messages[-1].get("content") != pregunta_usuario:
            st.session_state.chat_messages.append({"role": "user", "content": pregunta_usuario})
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(pregunta_usuario)
            
        with st.chat_message("assistant", avatar="🏛️"):
            with st.spinner(f"{nombre_agente} analizando la cuestión y orquestando herramientas..."):
                # Carga dinámica de credenciales actualizadas (session_state, secrets, .env)
                api_key_activa = get_gemini_api_key()
                groq_key_activa = get_groq_api_key()
                gemini_2_activa = get_secondary_gemini_api_key()

                motor_pref_sel = st.session_state.get("motor_ia_preferido", "Auto")
                proveedor_pref = "groq" if "Groq" in motor_pref_sel and "Auto" not in motor_pref_sel else "gemini"

                if not api_key_activa and not groq_key_activa:
                    st.error("Configura tu GEMINI_API_KEY o tu clave gratuita de Groq (GROQ_API_KEY) en el panel lateral.")
                    st.stop()
                    
                client = genai.Client(api_key=api_key_activa) if api_key_activa else None
                
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
                hora_esp = obtener_hora_espana()
                ts_inicio = hora_esp.strftime("%H:%M:%S")
                fecha_completa = hora_esp.strftime("%d/%m/%Y %H:%M:%S")

                # 2. Span de Inferencia LLM con Presupuesto de Tokens y Optimización de Pensamiento
                response, error_diag = None, None
                thinking_cfg = types.ThinkingConfig(thinking_budget=0) if es_ejecutivo else None
                gen_config = types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    thinking_config=thinking_cfg
                )
                modelo_efectivo = "llama-3.3-70b-versatile" if proveedor_pref == "groq" else modelo_activo
                with trace.span(
                    f"Inferencia LLM ({'Groq LPU (Llama 3.3 70B)' if proveedor_pref == 'groq' else modelo_activo})",
                    SpanType.LLM,
                    inputs={
                        "modelo": modelo_efectivo,
                        "modo": "ejecutivo" if es_ejecutivo else "detallado",
                        "max_tokens": max_tokens,
                        "prompt_chars": len(prompt_completo),
                        "proveedor_preferido": proveedor_pref
                    }
                ) as s_llm:
                    response, error_diag = generar_con_reintento(
                        client=client,
                        contents=prompt_completo,
                        model=modelo_activo,
                        config=gen_config,
                        groq_key=groq_key_activa,
                        gemini_key_2=gemini_2_activa,
                        proveedor_preferido=proveedor_pref,
                        max_tokens=max_tokens
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

                    err_msg_id = f"err_{int(time.time()*1000)}"
                    # Tarjeta de Explicabilidad DevOps y Diagnóstico Causal
                    render_error_diagnosis_card(error_diag, key_prefix=err_msg_id)

                    with st.expander("🔍 Observabilidad & Spans de Agentes (Google ADK)", expanded=True):
                        render_observability_panel(trace_dict, key_prefix="chat_current_err")

                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": "",
                        "error_diag": error_diag,
                        "trace": trace_dict,
                        "id": err_msg_id
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
                    trace_dict["modelo"] = getattr(response, "model", modelo_activo)
                    trace_dict["proveedor"] = getattr(response, "provider", "gemini")
                    trace_dict["es_failover"] = getattr(response, "es_failover", False)
                    trace_dict["modo_respuesta"] = "⚡ Ejecutivo" if es_ejecutivo else "📑 Detallado"
                    trace_dict["tokens_in"] = tokens_in
                    trace_dict["tokens_out"] = tokens_out
                    trace_dict["tokens_total"] = tokens_in + tokens_out
                    trace_dict["system_prompt"] = prompt_sistema.strip()
                    trace_dict["timestamp"] = ts_inicio
                    trace_dict["duracion"] = duracion

                    # Aviso informativo si se activó failover automático a Groq
                    if getattr(response, "es_failover", False):
                        st.info("🚀 **Failover Automático Activo:** Debido a la saturación transitoria de cuota de Google Gemini (15 RPM), esta consulta se resolvió instantáneamente mediante **Groq LPU (Llama 3.3 70B)** sin interrupciones ni coste.")
                    elif getattr(response, "provider", "gemini") == "groq":
                        st.caption("🚀 *Inferencia ejecutada en Groq Cloud LPU (Llama 3.3 70B - 30 RPM / 0,00 €)*")

                    st.markdown(response.text)

                    with st.expander("🔍 Observabilidad & Spans de Agentes (Google ADK)", expanded=True):
                        render_observability_panel(trace_dict, key_prefix="chat_current")

                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": response.text,
                        "trace": trace_dict,
                        "es_failover": getattr(response, "es_failover", False),
                        "provider": getattr(response, "provider", "gemini")
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
    st.markdown("Registro persistente e inmutable de todas las consultas sobre la gobernanza de España realizadas al gabinete por la ciudadanía.")
    
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
    st.subheader("🗳️ Votación Ciudadana y Buzón de Aportaciones")
    st.markdown("Participación ciudadana real: evalúa la propuesta política del Partido Tecnocrático de España y aporta tus críticas constructivas o iniciativas.")
    
    datos_voto = cargar_datos_comunidad()
    
    # 1. Sistema de votación real
    st.markdown("#### 1. Aprobación Ciudadana del Proyecto Político")
    
    col_vote1, col_vote2, col_stat = st.columns([1, 1, 2])
    
    with col_vote1:
        if st.button("👍 Apoyo el proyecto", use_container_width=True, disabled=st.session_state.ha_votado):
            registrar_voto(True)
            st.session_state.ha_votado = True
            st.success("¡Gracias por tu apoyo al Partido Tecnocrático de España!")
            st.rerun()
            
    with col_vote2:
        if st.button("👎 No me convence la propuesta", use_container_width=True, disabled=st.session_state.ha_votado):
            registrar_voto(False)
            st.session_state.ha_votado = True
            st.info("Voto registrado. Te invitamos a dejarnos tu crítica razonada en el buzón inferior.")
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
    st.markdown("#### 2. Buzón de Propuestas y Crítica Ciudadana para España")
    
    with st.form("form_buzon"):
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            autor_opinion = st.text_input("Tu nombre o alias (opcional):", placeholder="Ej: Ciudadano / Simpatizante")
        with col_f2:
            mensaje_opinion = st.text_area("¿Qué opinas de la propuesta de tecnocracia para España? ¿Qué medidas añadirías?", placeholder="Escribe aquí tu aportación o propuesta...")
            
        enviar_opinion = st.form_submit_button("📩 Enviar Opinión")
        
        if enviar_opinion:
            if not mensaje_opinion.strip():
                st.warning("Escribe algún comentario antes de enviar.")
            else:
                nueva_op = {
                    "autor": autor_opinion.strip() if autor_opinion.strip() else "Ciudadano Anónimo",
                    "mensaje": mensaje_opinion.strip(),
                    "fecha": obtener_hora_espana().strftime("%d/%m/%Y %H:%M")
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
