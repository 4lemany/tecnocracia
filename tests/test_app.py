"""
Tests unitarios para la lógica interna de app.py (Evaluación ADK y gestión de datos).
"""
import unittest
from evaluacion import evaluar_respuesta_adk
from storage import cargar_datos_comunidad


class TestAppLogic(unittest.TestCase):

    def test_evaluacion_adk_saludo(self):
        """Valida la métrica de fidelidad y coherencia cuando el usuario saluda."""
        eval_res = evaluar_respuesta_adk(
            agente="primer_ministro",
            pregunta="Hola, ¿quién eres?",
            respuesta="Hola ciudadano, soy el Primer Ministro del gabinete tecnocrático.",
            duracion=1.2,
            tokens_in=15,
            tokens_out=25
        )
        self.assertGreaterEqual(eval_res["score_global"], 90.0)
        self.assertEqual(eval_res["fidelidad"], 98)
        self.assertEqual(eval_res["grade_latencia"], "A+ (Ultra Rápida)")
        self.assertEqual(eval_res["seguridad"], "PASSED (100%)")
        self.assertGreater(eval_res["tok_per_sec"], 0)

    def test_evaluacion_adk_consulta_tecnica(self):
        """Valida la evaluación para una consulta técnica profunda."""
        eval_res = evaluar_respuesta_adk(
            agente="ministro_economia",
            pregunta="¿Cuál es la tasa de inflación y cómo afecta al presupuesto?",
            respuesta="De acuerdo con los datos oficiales del INE, el IPC se sitúa en el 2.9% y la inflación subyacente en el 2.7%. Por ello recomendamos mantener la prudencia fiscal y optimizar las partidas de gasto superfluo.",
            duracion=3.1,
            tokens_in=45,
            tokens_out=60
        )
        self.assertGreaterEqual(eval_res["score_global"], 85.0)
        self.assertEqual(eval_res["fidelidad"], 96)
        self.assertEqual(eval_res["grade_latencia"], "A (Rápida)")
        self.assertEqual(eval_res["seguridad"], "PASSED (100%)")

    def test_cargar_datos_comunidad(self):
        """Valida la carga de estructura de datos comunitaria."""
        datos = cargar_datos_comunidad()
        self.assertIsInstance(datos, dict)
        self.assertIn("votos", datos)
        self.assertIn("positivos", datos["votos"])
        self.assertIn("negativos", datos["votos"])
        self.assertIn("opiniones", datos)
        self.assertIn("historial_conversaciones", datos)


if __name__ == "__main__":
    unittest.main()
