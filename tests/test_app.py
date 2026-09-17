"""
Tests unitarios para la lógica interna de app.py (Evaluación ADK y gestión de datos).
"""
import unittest
from services.evaluacion import evaluar_respuesta_adk
from services.storage import cargar_datos_comunidad


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

    def test_backup_y_restauracion_comunidad(self):
        """Valida la exportación en JSON y la restauración segura de datos."""
        from services.storage import exportar_datos_comunidad_json, restaurar_datos_comunidad, get_storage_backend_info
        
        info = get_storage_backend_info()
        self.assertIn("tipo", info)
        self.assertIn("nombre", info)

        json_export = exportar_datos_comunidad_json()
        self.assertIsInstance(json_export, str)
        self.assertIn("votos", json_export)

        # Test de restauración con datos de prueba
        datos_prueba = {
            "votos": {"positivos": 42, "negativos": 3},
            "opiniones": [{"autor": "Ciudadano Test", "mensaje": "Todo OK", "fecha": "2026-09-17 16:00:00"}],
            "historial_conversaciones": []
        }
        ok = restaurar_datos_comunidad(datos_prueba)
        self.assertTrue(ok)

        datos_restaurados = cargar_datos_comunidad()
        self.assertEqual(datos_restaurados["votos"]["positivos"], 42)
        self.assertEqual(len(datos_restaurados["opiniones"]), 1)

    def test_metricas_cuota_gemini(self):
        """Valida el cálculo de consumo diario, límites Free Tier y tiempo de recarga UTC."""
        from services.storage import obtener_metricas_cuota_gemini
        
        datos_simulados = {
            "votos": {"positivos": 0, "negativos": 0},
            "opiniones": [],
            "historial_conversaciones": [
                {
                    "fecha": "2026-09-17 14:00:00",
                    "telemetria": {"tokens_in": 100, "tokens_out": 150, "tokens_total": 250, "timestamp": 1726588000}
                },
                {
                    "fecha": "2026-09-17 14:05:00",
                    "telemetria": {"tokens_in": 200, "tokens_out": 300, "tokens_total": 500, "timestamp": "2026-09-17 14:05:00"}
                }
            ]
        }
        cuota = obtener_metricas_cuota_gemini(datos_simulados)
        self.assertEqual(cuota["limite_rpd"], 1500)
        self.assertEqual(cuota["limite_rpm"], 15)
        self.assertEqual(cuota["peticiones_hoy"], 2)
        self.assertEqual(cuota["tokens_hoy"], 750)
        self.assertIn("tiempo_restante_reset", cuota)
        self.assertIn("00:00 UTC", cuota["proximo_reset_hora"])
        self.assertIn("Free Tier", cuota["coste"])


if __name__ == "__main__":
    unittest.main()


