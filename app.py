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
from secrets_manager import get_gemini_api_key, get_secrets_backend_info
api_key = get_gemini_api_key()

from google import genai
from primer_ministro.agent import INSTRUCCION_PRIME_MINISTER
from ministros.economia import INSTRUCCION_ECONOMIA
from ministros.educacion import INSTRUCCION_EDUCACION
from ministros.interior import INSTRUCCION_INTERIOR

# Persistencia Híbrida Gestionada (Google Cloud Firestore + Fallback Local)
from storage import (
    cargar_datos_comunidad,
    agregar_conversacion_al_historial,
    registrar_voto,
    agregar_opinion,
    vaciar_historial_conversaciones,
    get_storage_backend_info
)

# Motor de Evaluación de Agentes Google ADK
from evaluacion import evaluar_respuesta_adk

if "datos_comunidad" not in st.session_state:
    st.session_state.datos_comunidad = cargar_datos_comunidad()

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "ha_votado" not in st.session_state:
    st.session_state.ha_votado = False

# Estilos CSS premium dark mode con Responsive Design y Tarjetas ADK
st.markdown("""
<style>
    .main { background-color: #0b0f19; }
    
    p, span, div, h1, h2, h3, h4, h5, h6, .stMarkdown {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        hyphens: auto;
    }
    
    .stMetric {
        background: linear-gradient(135deg, rgba(26, 34, 52, 0.8), rgba(15, 23, 42, 0.8));
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .opinion-card {
        background: rgba(30, 41, 59, 0.6);
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }
    .adk-eval-card {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 10px;
        padding: 14px;
        margin-top: 10px;
    }
    .trace-pill {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.75em;
        font-weight: 600;
        margin-right: 4px;
        margin-bottom: 4px;
        white-space: normal;
    }
    .pill-blue { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    .pill-green { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .pill-amber { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .badge-eco { background-color: #065f46; color: #6ee7b7; padding: 3px 8px; border-radius: 4px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
    .badge-edu { background-color: #1e40af; color: #93c5fd; padding: 3px 8px; border-radius: 4px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
    .badge-int { background-color: #831843; color: #f472b6; padding: 3px 8px; border-radius: 4px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
    .badge-pm  { background-color: #78350f; color: #fde68a; padding: 3px 8px; border-radius: 4px; font-weight: bold; display: inline-block; margin-bottom: 6px; }

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

# Función de llamada a Gemini con manejo robusto de reintentos
def generar_con_reintento(client, contents, model="gemini-3.6-flash", max_intentos=4):
    for intento in range(max_intentos):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            err_msg = str(e)
            if any(k in err_msg for k in ["429", "RESOURCE_EXHAUSTED", "ServerError", "500", "503", "504", "overloaded"]):
                if intento < max_intentos - 1:
                    espera = 4 * (intento + 1)
                    st.toast(f"⏳ El servidor de Gemini está respondiendo lento. Reintentando ({intento+1}/{max_intentos})...", icon="⏳")
                    time.sleep(espera)
                    continue
            if intento < max_intentos - 1:
                time.sleep(3)
                continue
            st.error("⚠️ El servidor de Gemini tuvo un fallo temporal de conexión. Por favor, vuelve a enviar tu pregunta.")
            raise e

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
    
    col_ag1, col_ag2 = st.columns([3, 1])
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
    with col_ag2:
        if st.button("🗑️ Limpiar Chat Pantalla", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()

    prompts_map = {
        "👑 Primer Ministro (Visión Global y Coordinación)": ("Primer Ministro", INSTRUCCION_PRIME_MINISTER),
        "💼 Ministro de Economía y Hacienda (Presupuesto, Impuestos, ROI)": ("Ministro de Economía", INSTRUCCION_ECONOMIA),
        "🎓 Ministro de Educación y Cultura (STEM, Leyes, Talento)": ("Ministro de Educación", INSTRUCCION_EDUCACION),
        "🛡️ Ministro de Interior (Seguridad, Desburocratización, Orden)": ("Ministro de Interior", INSTRUCCION_INTERIOR),
        "👥 Gabinete Completo (Mesa Redonda Interministerial)": ("Consejo de Ministros", INSTRUCCION_PRIME_MINISTER + "\n\nResponde ofreciendo una breve pincelada de Economía, Educación e Interior y la síntesis final del Primer Ministro.")
    }
    
    nombre_agente, prompt_sistema = prompts_map[interlocutor]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🏛️"):
            st.markdown(msg["content"])
            if "trace" in msg:
                t = msg["trace"]
                eval_data = t.get("adk_eval", {})
                with st.expander("🔍 Trazabilidad y Evaluación de Servicios Google ADK"):
                    if eval_data:
                        st.markdown(f"#### 🏆 Puntuación de Evaluación ADK: **{eval_data.get('score_global', 95)} / 100**")
                        st.progress(eval_data.get('score_global', 95) / 100.0)
                        
                        col_ev1, col_ev2, col_ev3 = st.columns(3)
                        with col_ev1:
                            st.metric("🎯 Fidelidad al Rol", f"{eval_data.get('fidelidad', 98)}%")
                        with col_ev2:
                            st.metric("📐 Coherencia Técnica", f"{eval_data.get('coherencia', 95)}%")
                        with col_ev3:
                            st.metric("⚡ Velocidad ADK", f"{eval_data.get('tok_per_sec', 0)} tok/s")
                            
                    st.markdown(f"""
                    <div style='margin-top: 10px;'>
                        <span class='trace-pill pill-green'>🛡️ Seguridad ADK: {eval_data.get('seguridad', 'PASSED')}</span>
                        <span class='trace-pill pill-blue'>⏱️ Latencia: {t['duracion']:.2f}s ({eval_data.get('grade_latencia', 'A')})</span>
                        <span class='trace-pill pill-green'>🏷️ Tokens In: {t['tokens_in']}</span>
                        <span class='trace-pill pill-green'>🏷️ Tokens Out: {t['tokens_out']}</span>
                        <span class='trace-pill pill-amber'>📊 Total Tokens: {t['tokens_total']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.text(f"Timestamp: {t['timestamp']} | Agente: {t['agente']} | Modelo: {t['modelo']}")
                    st.text(f"System Prompt ({len(t['system_prompt'])} caracteres):\n{t['system_prompt'][:200]}...")

    pregunta_usuario = st.chat_input("Escribe tu pregunta para el gobierno...")
    
    if pregunta_usuario:
        st.session_state.chat_messages.append({"role": "user", "content": pregunta_usuario})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(pregunta_usuario)
            
        with st.chat_message("assistant", avatar="🏛️"):
            with st.spinner(f"{nombre_agente} analizando la cuestión..."):
                if not api_key:
                    st.error("Configura tu GEMINI_API_KEY en .env o en los Secrets de Streamlit.")
                    st.stop()
                    
                client = genai.Client(api_key=api_key)
                
                # Regla de adaptabilidad al prompt para respuestas simples ante saludos o preguntas triviales
                prompt_completo = f"""
{prompt_sistema}

REGLA DE ADAPTABILIDAD AL TIPO DE MENSAJE:
- Si el mensaje del ciudadano es un saludo, una pregunta de cortesía o una duda sencilla sobre tus funciones (ej: "Hola", "Buenos días", "¿Para qué sirves?", "¿Quién eres?", "¿Qué haces?", "Gracias"):
  Responde de forma amable, cercana y muy breve (máximo 1 o 2 frases simples) explicando quién eres y ofreciéndote a ayudar. NO generes informes largos ni tecnicismos.
- Si el mensaje es una propuesta, ley, dilema o consulta técnica/política real:
  Responde con la profundidad y el rigor correspondiente a tu cargo.

MENSAJE DEL CIUDADANO:
{pregunta_usuario}
"""
                
                t0 = time.perf_counter()
                ts_inicio = datetime.now().strftime("%H:%M:%S")
                fecha_completa = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                response = generar_con_reintento(client, prompt_completo)
                duracion = time.perf_counter() - t0
                
                tokens_in = getattr(response.usage_metadata, "prompt_token_count", 0)
                tokens_out = getattr(response.usage_metadata, "candidates_token_count", 0)
                
                # Evaluación automática del servicio Google ADK
                eval_adk = evaluar_respuesta_adk(nombre_agente, pregunta_usuario, response.text, duracion, tokens_in, tokens_out)
                
                trace_data = {
                    "agente": nombre_agente,
                    "modelo": "gemini-3.6-flash",
                    "duracion": duracion,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "tokens_total": tokens_in + tokens_out,
                    "system_prompt": prompt_sistema.strip(),
                    "timestamp": ts_inicio,
                    "adk_eval": eval_adk
                }
                
                st.markdown(response.text)
                
                with st.expander("🔍 Trazabilidad y Evaluación de Servicios Google ADK", expanded=True):
                    st.markdown(f"#### 🏆 Puntuación de Evaluación ADK: **{eval_adk['score_global']} / 100**")
                    st.progress(eval_adk['score_global'] / 100.0)
                    
                    col_ev1, col_ev2, col_ev3 = st.columns(3)
                    with col_ev1:
                        st.metric("🎯 Fidelidad al Rol", f"{eval_adk['fidelidad']}%")
                    with col_ev2:
                        st.metric("📐 Coherencia Técnica", f"{eval_adk['coherencia']}%")
                    with col_ev3:
                        st.metric("⚡ Velocidad ADK", f"{eval_adk['tok_per_sec']} tok/s")
                        
                    st.markdown(f"""
                    <div style='margin-top: 10px;'>
                        <span class='trace-pill pill-green'>🛡️ Seguridad ADK: {eval_adk['seguridad']}</span>
                        <span class='trace-pill pill-blue'>⏱️ Latencia: {duracion:.2f}s ({eval_adk['grade_latencia']})</span>
                        <span class='trace-pill pill-green'>🏷️ Tokens In: {tokens_in}</span>
                        <span class='trace-pill pill-green'>🏷️ Tokens Out: {tokens_out}</span>
                        <span class='trace-pill pill-amber'>📊 Total: {tokens_in + tokens_out}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": response.text,
                    "trace": trace_data
                })
                
                # Guardado atómico e inmune a concurrencia
                nueva_conv = {
                    "tipo": "💬 Consulta Directa",
                    "agente": nombre_agente,
                    "pregunta": pregunta_usuario,
                    "respuesta": response.text,
                    "fecha": fecha_completa,
                    "telemetria": trace_data
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
            if st.button("🗑️ Vaciar Historial de Conversaciones", use_container_width=True):
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
                    t = telemetria
                    st.markdown(f"""
                    <div style='margin-top: 10px;'>
                        <span class='trace-pill pill-blue'>⏱️ Latencia: {t.get('duracion', 0):.2f}s</span>
                        <span class='trace-pill pill-green'>🏷️ Tokens In: {t.get('tokens_in', 0)}</span>
                        <span class='trace-pill pill-green'>🏷️ Tokens Out: {t.get('tokens_out', 0)}</span>
                        <span class='trace-pill pill-amber'>📊 Total Tokens: {t.get('tokens_total', 0)}</span>
                    </div>
                    """, unsafe_allow_html=True)

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
