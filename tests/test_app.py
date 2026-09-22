from datetime import datetime, timezone
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
            "opiniones": [{"autor": "Ciudadano Test", "mensaje": "Todo OK", "fecha": f"2026-09-22 16:00:00"}],
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
                    "fecha": f"2026-09-22 14:00:00",
                    "telemetria": {"tokens_in": 100, "tokens_out": 150, "tokens_total": 250, "timestamp": 1726588000}
                },
                {
                    "fecha": f"2026-09-22 14:05:00",
                    "telemetria": {"tokens_in": 200, "tokens_out": 300, "tokens_total": 500, "timestamp": f"2026-09-22 14:05:00"}
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

    def test_secrets_manager_groq_and_secondary(self):
        """Valida que los getters de Groq y Gemini Secundario existan y funcionen."""
        from services.secrets_manager import get_groq_api_key, get_secondary_gemini_api_key
        # En entorno de pruebas sin env vars devuelven None sin lanzar excepción
        self.assertIsNone(get_groq_api_key())
        self.assertIsNone(get_secondary_gemini_api_key())

    def test_groq_inference_mock(self):
        """Valida la inferencia con Groq simulando la API REST de Groq Cloud."""
        from unittest.mock import patch, MagicMock
        from app import generar_con_groq

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            "choices": [{"message": {"content": "Respuesta simulada de Llama 3.3 70B en Groq"}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 80}
        }

        with patch("requests.post", return_value=fake_resp):
            resp, diag = generar_con_groq("Hola", groq_key="gsk_fakekey123")
            self.assertIsNone(diag)
            self.assertIsNotNone(resp)
            self.assertEqual(resp.text, "Respuesta simulada de Llama 3.3 70B en Groq")
            self.assertEqual(resp.provider, "groq")
            self.assertEqual(resp.usage_metadata.prompt_token_count, 50)
            self.assertEqual(resp.usage_metadata.candidates_token_count, 80)

    def test_failover_gemini_to_groq_on_429(self):
        """Valida que cuando Gemini arroja 429 RESOURCE_EXHAUSTED, se conmuta automáticamente a Groq."""
        from unittest.mock import patch, MagicMock
        from app import generar_con_reintento

        # Mock client de Gemini que falla con 429
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("ClientError: 429 RESOURCE_EXHAUSTED. Quota exceeded.")

        fake_groq_resp = MagicMock()
        fake_groq_resp.status_code = 200
        fake_groq_resp.json.return_value = {
            "choices": [{"message": {"content": "Respuesta generada vía Failover a Groq LPU"}}],
            "usage": {"prompt_tokens": 40, "completion_tokens": 60}
        }

        with patch("requests.post", return_value=fake_groq_resp):
            resp, diag = generar_con_reintento(
                client=mock_client,
                contents="Consulta económica",
                groq_key="gsk_failover_test",
                max_intentos=1
            )
            self.assertIsNone(diag)
            self.assertIsNotNone(resp)
            self.assertEqual(resp.text, "Respuesta generada vía Failover a Groq LPU")
            self.assertEqual(resp.provider, "groq")
            self.assertTrue(resp.es_failover)

    def test_fallback_groq_to_gemini_when_groq_fails(self):
        """Valida la estrategia inversa: Groq como primario con fallback a Gemini si Groq falla."""
        from unittest.mock import patch, MagicMock
        from app import generar_con_reintento

        # Groq falla con 500
        fake_groq_error = MagicMock()
        fake_groq_error.status_code = 500
        fake_groq_error.json.return_value = {"error": {"message": "Groq service temporary error"}}

        # Gemini responde con éxito
        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = "Respuesta de respaldo servida por Google Gemini"
        mock_gemini_resp.usage_metadata = MagicMock()
        mock_gemini_resp.usage_metadata.prompt_token_count = 35
        mock_gemini_resp.usage_metadata.candidates_token_count = 55
        mock_gemini_resp.candidates = []

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_gemini_resp

        with patch("requests.post", return_value=fake_groq_error):
            resp, diag = generar_con_reintento(
                client=mock_client,
                contents="Pregunta de contingencia",
                groq_key="gsk_failing_key",
                proveedor_preferido="groq",
                max_intentos=1
            )
            self.assertIsNone(diag)
            self.assertIsNotNone(resp)
            self.assertEqual(resp.text, "Respuesta de respaldo servida por Google Gemini")
            self.assertEqual(resp.provider, "gemini")
            self.assertTrue(resp.es_failover)
            self.assertEqual(resp.failover_desde, "groq")


if __name__ == "__main__":
    unittest.main()


