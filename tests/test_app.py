"""
Tests unitarios para la lógica interna de app.py (Evaluación ADK y gestión de datos).
"""
import pytest
from app import evaluar_respuesta_adk, cargar_datos_comunidad

def test_evaluacion_adk_saludo():
    """Valida la métrica de fidelidad y coherencia cuando el usuario saluda."""
    eval_res = evaluar_respuesta_adk(
        agente="primer_ministro",
        pregunta="Hola, ¿quién eres?",
        respuesta="Hola ciudadano, soy el Primer Ministro del gabinete tecnocrático.",
        duracion=1.2,
        tokens_in=15,
        tokens_out=25
    )
    assert eval_res["score_global"] >= 90.0
    assert eval_res["fidelidad"] == 98
    assert eval_res["grade_latencia"] == "A+ (Ultra Rápida)"
    assert eval_res["seguridad"] == "PASSED (100%)"
    assert eval_res["tok_per_sec"] > 0

def test_evaluacion_adk_consulta_tecnica():
    """Valida la evaluación para una consulta técnica profunda."""
    eval_res = evaluar_respuesta_adk(
        agente="ministro_economia",
        pregunta="¿Cuál es la tasa de inflación y cómo afecta al presupuesto?",
        respuesta="De acuerdo con los datos oficiales del INE, el IPC se sitúa en el 2.9% y la inflación subyacente en el 2.7%. Por ello recomendamos mantener la prudencia fiscal y optimizar las partidas de gasto superfluo.",
        duracion=3.1,
        tokens_in=45,
        tokens_out=60
    )
    assert eval_res["score_global"] >= 85.0
    assert eval_res["fidelidad"] == 96
    assert eval_res["grade_latencia"] == "A (Rápida)"
    assert eval_res["seguridad"] == "PASSED (100%)"

def test_cargar_datos_comunidad():
    """Valida la carga de estructura de datos comunitaria."""
    datos = cargar_datos_comunidad()
    assert isinstance(datos, dict)
    assert "votos" in datos
    assert "positivos" in datos["votos"]
    assert "negativos" in datos["votos"]
    assert "opiniones" in datos
    assert "historial_conversaciones" in datos
