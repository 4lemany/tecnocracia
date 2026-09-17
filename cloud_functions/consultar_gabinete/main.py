"""
Google Cloud Function (2ª Gen / Cloud Run functions) - Consulta Serverless al Gabinete Tecnocrático.
100% Gratuito: 2 millones de invocaciones al mes incluidas en el Always Free Tier de GCP.
"""
import os
import json
import functions_framework
from google import genai

@functions_framework.http
def consultar_gabinete(request):
    """Punto de entrada HTTP serverless para interactuar con los ministros."""
    # Cabeceras CORS para permitir peticiones web
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Content-Type': 'application/json; charset=utf-8'
    }

    if request.method == 'OPTIONS':
        return ('', 204, headers)

    request_json = request.get_json(silent=True)
    params = request.args

    agente = "primer_ministro"
    pregunta = ""

    if request_json:
        agente = request_json.get("agente", agente)
        pregunta = request_json.get("pregunta", "")
    elif params:
        agente = params.get("agente", agente)
        pregunta = params.get("pregunta", "")

    if not pregunta:
        return (json.dumps({
            "error": "Parámetro 'pregunta' requerido.",
            "ejemplo": {"agente": "primer_ministro", "pregunta": "¿Cuál es la propuesta para reducir el desempleo juvenil?"}
        }, ensure_ascii=False), 400, headers)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return (json.dumps({"error": "GEMINI_API_KEY no configurada en el entorno de Cloud Functions."}, ensure_ascii=False), 500, headers)

    client = genai.Client(api_key=api_key)

    prompts_sistema = {
        "primer_ministro": "Eres el Primer Ministro y líder del Partido Tecnocrático de España. Coordina la propuesta de gobernanza para España con máximo rigor técnico, datos empíricos y superación del partidismo ideológico.",
        "economia": "Eres el Ministro de Economía y Hacienda del Partido Tecnocrático de España. Analiza la economía española con rigor presupuestario, control de deuda pública, fiscalidad eficiente y fomento de la productividad.",
        "educacion": "Eres el Ministro de Educación y Formación Profesional del Partido Tecnocrático de España. Prioriza el capital humano, la FP Dual, las competencias STEM y la excelencia formativa en España.",
        "interior": "Eres el Ministro del Interior y Gobernación del Partido Tecnocrático de España. Prioriza la ciberseguridad nacional, la desburocratización del Estado, la meritocracia administrativa y la protección civil en España."
    }

    instruccion = prompts_sistema.get(agente, prompts_sistema["primer_ministro"])

    try:
        response = client.models.generate_content(
            model=os.getenv("MODEL_NAME", "gemini-3.6-flash"),
            contents=f"Instrucción de rol: {instruccion}\n\nPregunta ciudadana: {pregunta}"
        )
        return (json.dumps({
            "agente": agente,
            "pregunta": pregunta,
            "respuesta": response.text,
            "status": "success"
        }, ensure_ascii=False), 200, headers)
    except Exception as e:
        return (json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False), 500, headers)
