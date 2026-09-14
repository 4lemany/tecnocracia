"""
🏛️ Tecnocracia: Plataforma de Gobierno Multiagente con Google ADK y Gemini.
Deliberación Ministerial, Chat Libre con Trazabilidad, Votación Comunitaria y Buzón de Opiniones.
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Configuración de página de Streamlit
st.set_page_config(
    page_title="Tecnocracia | Partido y Gobierno Multiagente",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar entorno y API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

from google import genai
from primer_ministro.agent import INSTRUCCION_PRIME_MINISTER
from ministros.economia import INSTRUCCION_ECONOMIA
from ministros.educacion import INSTRUCCION_EDUCACION
from ministros.interior import INSTRUCCION_INTERIOR

# Gestión persistente de votos y buzón comunitario
RUTA_COMUNIDAD = Path("datos_comunidad.json")

def cargar_datos_comunidad():
    if not RUTA_COMUNIDAD.exists():
        datos_default = {
            "votos": {"positivos": 14, "negativos": 2},
            "opiniones": [
                {
                    "autor": "Carlos (Ingeniero)",
                    "mensaje": "Gran idea contrastar a los ministros antes de dar una resolución. Da mucha más riqueza al debate.",
                    "fecha": "14/09/2026 18:25"
                },
                {
                    "autor": "Elena M.",
                    "mensaje": "El ministro de economía es implacable con el presupuesto, pero el de educación compensa bien con visión a largo plazo.",
                    "fecha": "14/09/2026 18:40"
                }
            ]
        }
        with open(RUTA_COMUNIDAD, "w", encoding="utf-8") as f:
            json.dump(datos_default, f, ensure_ascii=False, indent=2)
        return datos_default
    try:
        with open(RUTA_COMUNIDAD, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"votos": {"positivos": 0, "negativos": 0}, "opiniones": []}

def guardar_datos_comunidad(datos):
    with open(RUTA_COMUNIDAD, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

if "datos_comunidad" not in st.session_state:
    st.session_state.datos_comunidad = cargar_datos_comunidad()

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "ha_votado" not in st.session_state:
    st.session_state.ha_votado = False

# Estilos CSS premium dark mode
st.markdown("""
<style>
    .main { background-color: #0b0f19; }
    .stMetric {
        background: linear-gradient(135deg, rgba(26, 34, 52, 0.8), rgba(15, 23, 42, 0.8));
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .opinion-card {
        background: rgba(30, 41, 59, 0.6);
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .trace-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 9999px;
        font-size: 0.75em;
        font-weight: 600;
        margin-right: 6px;
    }
    .pill-blue { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    .pill-green { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .pill-amber { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .badge-eco { background-color: #065f46; color: #6ee7b7; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
    .badge-edu { background-color: #1e40af; color: #93c5fd; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
    .badge-int { background-color: #831843; color: #f472b6; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
    .badge-pm  { background-color: #78350f; color: #fde68a; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Función de llamada a Gemini con reintento automático
def generar_con_reintento(client, contents, model="gemini-3.6-flash", max_intentos=3):
    for intento in range(max_intentos):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                if intento < max_intentos - 1:
                    espera = 25
                    if "retry in " in err_msg:
                        try:
                            espera = int(float(err_msg.split("retry in ")[1].split("s")[0])) + 2
                        except Exception:
                            espera = 25
                    st.toast(f"⏳ Pausa de cuota gratuita. Esperando {espera}s...", icon="⏳")
                    time.sleep(espera)
                    continue
                else:
                    st.error("⚠️ Límite temporal de peticiones alcanzado. Espera 30 segundos y vuelve a probar.")
                    raise e
            else:
                raise e

# ----------------- BARRA LATERAL: INFORMACIÓN Y APROBACIÓN -----------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/courthouse.png", width=64)
    st.title("Gobierno Tecnocrático")
    st.caption("Sistema Multiagente impulsado por Google ADK & Gemini")
    
    st.divider()
    
    # Métricas de votación ciudadana en el sidebar
    votos = st.session_state.datos_comunidad["votos"]
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
    st.caption(f"👍 {pos} votos a favor | 👎 {neg} en contra")
    
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
st.markdown("Un gobierno ficticio donde ministros con IA deliberan con máximo rigor técnico sobre cómo dirigir una región.")

tab1, tab2, tab3 = st.tabs([
    "🚀 Consejo de Ministros (Debate y Leyes)",
    "💬 Preguntas Libres y Trazabilidad",
    "🗳️ Votación y Buzón Ciudadano"
])

# -------------------------------------------------------------
# TAB 1: CONSEJO DE MINISTROS (DEBATE DELIBERATIVO REAL)
# -------------------------------------------------------------
with tab1:
    st.subheader("1. Plantea un dilema o propuesta para la región")
    
    casos_predeterminados = [
        "Plan de choque para reducir el desempleo juvenil mediante becas formativas en empresas de tecnología y transición ecológica.",
        "Crisis de vivienda: regulación del alquiler turístico y movilización de suelo público para viviendas de protección oficial.",
        "Plan de digitalización y desburocratización radical: reducir plazos de licencias administrativas con inteligencia artificial.",
        "Financiación del transporte público regional: gratuidad para jóvenes y trabajadores financiada con una tasa turística."
    ]
    
    modo = st.radio("Origen de la propuesta:", ["Elegir caso predeterminado", "Escribir propuesta personalizada"], horizontal=True)
    
    if modo == "Elegir caso predeterminado":
        propuesta_texto = st.selectbox("Selecciona un caso:", casos_predeterminados)
    else:
        propuesta_texto = st.text_area(
            "Escribe la propuesta o problema regional a debatir:",
            placeholder="Ej: ¿Qué opináis de poner peajes de acceso al centro de la ciudad para reducir la contaminación?...",
            height=100
        )
        
    btn_convocar = st.button("⚖️ Convocar Consejo de Ministros y Debatir", type="primary", use_container_width=True)
    
    if btn_convocar:
        if not api_key:
            st.error("❌ GEMINI_API_KEY no encontrada en .env. Por favor, configúrala.")
            st.stop()
            
        client = genai.Client(api_key=api_key)
        
        with st.status("🏛️ Consejo de Ministros en sesión deliberativa...", expanded=True) as status:
            
            # 1. Ministro de Economía
            st.write("💼 **1. Ministro de Economía analizando viabilidad presupuestaria y coste-beneficio...**")
            prompt_eco = f"""
{INSTRUCCION_ECONOMIA}

PROPUESTA REGIONAL A EVALUAR:
{propuesta_texto}

Genera tu dictamen ministerial económico (máx 3 párrafos).
Argumenta con lógica de sostenibilidad fiscal, incentivos económicos y posibles sobrecostes o retornos. Exige condiciones a los otros ministros.
"""
            res_eco = generar_con_reintento(client, prompt_eco)
            
            with st.expander("💼 Dictamen del Ministro de Economía", expanded=True):
                st.markdown("<span class='badge-eco'>ECONOMÍA & HACIENDA</span>", unsafe_allow_html=True)
                st.write(res_eco.text)
                
            time.sleep(1.0)
            
            # 2. Ministro de Educación y Cultura
            st.write("🎓 **2. Ministro de Educación evaluando impacto en capital humano y ciencia...**")
            prompt_edu = f"""
{INSTRUCCION_EDUCACION}

PROPUESTA REGIONAL A EVALUAR:
{propuesta_texto}

POSTURA PREVIA DEL MINISTRO DE ECONOMÍA:
{res_eco.text}

Emite tu dictamen ministerial (máx 3 párrafos). Defiende la formación, el talento, la investigación y contrarresta constructivamente la rigidez fiscal de Economía.
"""
            res_edu = generar_con_reintento(client, prompt_edu)
            
            with st.expander("🎓 Dictamen del Ministro de Educación y Ciencia", expanded=True):
                st.markdown("<span class='badge-edu'>EDUCACIÓN & CIENCIA</span>", unsafe_allow_html=True)
                st.write(res_edu.text)
                
            time.sleep(1.0)
            
            # 3. Ministro de Interior
            st.write("🛡️ **3. Ministro de Interior evaluando seguridad cívica y viabilidad operativa...**")
            prompt_int = f"""
{INSTRUCCION_INTERIOR}

PROPUESTA REGIONAL A EVALUAR:
{propuesta_texto}

PROPUESTA DE ECONOMÍA: {res_eco.text[:350]}
PROPUESTA DE EDUCACIÓN: {res_edu.text[:350]}

Emite tu dictamen ministerial (máx 3 párrafos). Evalúa el orden público, la seguridad jurídica, la desburocratización y la aceptación cívica de la medida.
"""
            res_int = generar_con_reintento(client, prompt_int)
            
            with st.expander("🛡️ Dictamen del Ministro de Interior", expanded=True):
                st.markdown("<span class='badge-int'>INTERIOR & GOBERNANZA</span>", unsafe_allow_html=True)
                st.write(res_int.text)
                
            time.sleep(1.0)
            
            # 4. Primer Ministro
            st.write("👑 **4. El Primer Ministro sintetiza el Dictamen Tecnocrático y el Hilo para Redes...**")
            prompt_pm = f"""
{INSTRUCCION_PRIME_MINISTER}

PROPUESTA ORIGINAL:
{propuesta_texto}

DEBATE DE LOS MINISTROS:
- ECONOMÍA: {res_eco.text}
- EDUCACIÓN: {res_edu.text}
- INTERIOR: {res_int.text}

Emite la resolución final estructurada:
1. VEREDICTO FINAL: [APROBADA CON CONDICIONES] o [VETADA POR INVIABILIDAD].
2. MEDIDAS EJECUTIVAS: 3 compromisos operativos consensuados.
3. HILO OFICIAL PARA REDES SOCIALES (Twitter/X e Instagram):
   - Tweet 1: Anuncio formal y veredicto con datos clave.
   - Tweet 2: Partida económica y condiciones técnicas.
   - Tweet 3: Garantías cívicas y plazos de ejecución.
   - Tweet 4: Mensaje pedagógico a los ciudadanos.
"""
            res_pm = generar_con_reintento(client, prompt_pm)
            status.update(label="✅ Consejo de Ministros finalizado. Dictamen emitido.", state="complete")
            
        st.divider()
        st.subheader("📜 Dictamen Oficial del Primer Ministro")
        st.markdown("<span class='badge-pm'>PRIMER MINISTRO</span>", unsafe_allow_html=True)
        st.markdown(res_pm.text)

# -------------------------------------------------------------
# TAB 2: PREGUNTAS LIBRES Y TRAZABILIDAD
# -------------------------------------------------------------
with tab2:
    st.subheader("💬 Consulta y Preguntas Libres al Gabinete")
    st.markdown("Pregunta cualquier cuestión a los miembros del gobierno y consulta la **trazabilidad técnica (tokens, latencia y system prompt)**.")
    
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
        if st.button("🗑️ Limpiar Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()

    prompts_map = {
        "👑 Primer Ministro (Visión Global y Coordinación)": ("Primer Ministro", INSTRUCCION_PRIME_MINISTER),
        "💼 Ministro de Economía y Hacienda (Presupuesto, Impuestos, ROI)": ("Ministro de Economía", INSTRUCCION_ECONOMIA),
        "🎓 Ministro de Educación y Cultura (STEM, Leyes, Talento)": ("Ministro de Educación", INSTRUCCION_EDUCACION),
        "🛡️ Ministro de Interior (Seguridad, Desburocratización, Orden)": ("Ministro de Interior", INSTRUCCION_INTERIOR),
        "👥 Gabinete Completo (Mesa Redonda Interministerial)": ("Consejo de Ministros", INSTRUCCION_PRIME_MINISTER + "\n\nResponde ofreciendo la postura de Economía, Educación e Interior y la síntesis final del Primer Ministro.")
    }
    
    nombre_agente, prompt_sistema = prompts_map[interlocutor]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🏛️"):
            st.markdown(msg["content"])
            if "trace" in msg:
                t = msg["trace"]
                with st.expander("🔍 Trazabilidad y Telemetría"):
                    st.markdown(f"""
                    <span class='trace-pill pill-blue'>⏱️ Latencia: {t['duracion']:.2f}s</span>
                    <span class='trace-pill pill-green'>🏷️ Tokens In: {t['tokens_in']}</span>
                    <span class='trace-pill pill-green'>🏷️ Tokens Out: {t['tokens_out']}</span>
                    <span class='trace-pill pill-amber'>📊 Total: {t['tokens_total']}</span>
                    <span class='trace-pill pill-blue'>🤖 Modelo: {t['modelo']}</span>
                    """, unsafe_allow_html=True)
                    st.text(f"Timestamp: {t['timestamp']} | Agente: {t['agente']}")
                    st.text(f"Prompt base ({len(t['system_prompt'])} caracteres):\n{t['system_prompt'][:250]}...")

    pregunta_usuario = st.chat_input("Escribe tu pregunta para el gobierno...")
    
    if pregunta_usuario:
        st.session_state.chat_messages.append({"role": "user", "content": pregunta_usuario})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(pregunta_usuario)
            
        with st.chat_message("assistant", avatar="🏛️"):
            with st.spinner(f"{nombre_agente} analizando la cuestión..."):
                if not api_key:
                    st.error("Configura tu GEMINI_API_KEY en .env")
                    st.stop()
                    
                client = genai.Client(api_key=api_key)
                prompt_completo = f"{prompt_sistema}\n\nPREGUNTA DEL CIUDADANO:\n{pregunta_usuario}\n\nResponde directamente con rigor técnico y honestidad."
                
                t0 = time.perf_counter()
                ts_inicio = datetime.now().strftime("%H:%M:%S")
                response = generar_con_reintento(client, prompt_completo)
                duracion = time.perf_counter() - t0
                
                tokens_in = getattr(response.usage_metadata, "prompt_token_count", 0)
                tokens_out = getattr(response.usage_metadata, "candidates_token_count", 0)
                
                trace_data = {
                    "agente": nombre_agente,
                    "modelo": "gemini-3.6-flash",
                    "duracion": duracion,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "tokens_total": tokens_in + tokens_out,
                    "system_prompt": prompt_sistema.strip(),
                    "timestamp": ts_inicio
                }
                
                st.markdown(response.text)
                
                with st.expander("🔍 Trazabilidad y Telemetría", expanded=True):
                    st.markdown(f"""
                    <span class='trace-pill pill-blue'>⏱️ Latencia: {duracion:.2f}s</span>
                    <span class='trace-pill pill-green'>🏷️ Tokens In: {tokens_in}</span>
                    <span class='trace-pill pill-green'>🏷️ Tokens Out: {tokens_out}</span>
                    <span class='trace-pill pill-amber'>📊 Total: {tokens_in + tokens_out}</span>
                    <span class='trace-pill pill-blue'>🤖 Modelo: gemini-3.6-flash</span>
                    """, unsafe_allow_html=True)
                
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": response.text,
                    "trace": trace_data
                })

# -------------------------------------------------------------
# TAB 3: VOTACIÓN COMUNITARIA Y BUZÓN DE CRÍTICAS
# -------------------------------------------------------------
with tab3:
    st.subheader("🗳️ ¿Qué te parece el proyecto de Gobierno Tecnocrático?")
    st.markdown("Tu opinión ayuda a mejorar el modelo de agentes y el rigor de los debates.")
    
    # 1. Sistema de votación
    st.markdown("#### 1. Votación de Aprobación de la Web")
    
    col_vote1, col_vote2, col_stat = st.columns([1, 1, 2])
    
    with col_vote1:
        if st.button("👍 Me gusta el proyecto", use_container_width=True, disabled=st.session_state.ha_votado):
            st.session_state.datos_comunidad["votos"]["positivos"] += 1
            guardar_datos_comunidad(st.session_state.datos_comunidad)
            st.session_state.ha_votado = True
            st.success("¡Gracias por tu voto a favor!")
            st.rerun()
            
    with col_vote2:
        if st.button("👎 No me convence", use_container_width=True, disabled=st.session_state.ha_votado):
            st.session_state.datos_comunidad["votos"]["negativos"] += 1
            guardar_datos_comunidad(st.session_state.datos_comunidad)
            st.session_state.ha_votado = True
            st.info("Voto registrado. Agradecemos que nos dejes tu crítica abajo.")
            st.rerun()
            
    with col_stat:
        v = st.session_state.datos_comunidad["votos"]
        total = v["positivos"] + v["negativos"]
        pct = round((v["positivos"] / total) * 100, 1) if total > 0 else 0
        st.markdown(f"**Resultado actual:** **{pct}% de aprobación** ({v['positivos']} a favor de {total} votos)")
        st.progress(pct / 100.0)
        
    if st.session_state.ha_votado:
        st.caption("✅ Ya has participado en la votación en esta sesión.")
        
    st.divider()
    
    # 2. Buzón de opiniones y críticas constructivas
    st.markdown("#### 2. Buzón de Críticas Constructivas y Sugerencias")
    
    with st.form("form_buzon"):
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            autor_opinion = st.text_input("Tu nombre o apodo (opcional):", placeholder="Ej: Anónimo / Alumno de Economía")
        with col_f2:
            mensaje_opinion = st.text_area("¿Qué opinas del proyecto? ¿Qué mejorarías?", placeholder="Escribe aquí tu crítica constructiva o propuesta técnica...")
            
        enviar_opinion = st.form_submit_button("📩 Enviar al Buzón Público")
        
        if enviar_opinion:
            if not mensaje_opinion.strip():
                st.warning("Escribe algún comentario antes de enviar.")
            else:
                nueva_op = {
                    "autor": autor_opinion.strip() if autor_opinion.strip() else "Ciudadano Anónimo",
                    "mensaje": mensaje_opinion.strip(),
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                st.session_state.datos_comunidad["opiniones"].append(nueva_op)
                guardar_datos_comunidad(st.session_state.datos_comunidad)
                st.success("¡Opinión añadida al buzón con éxito!")
                st.rerun()
                
    st.markdown("#### 📬 Opiniones de la Comunidad")
    opiniones = st.session_state.datos_comunidad.get("opiniones", [])
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
