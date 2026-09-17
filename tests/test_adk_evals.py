"""
🧪 Suite de Pruebas Automatizadas para CI/CD (Google ADK & Evals)
Valida la integridad de agentes, herramientas oficiales, datasets de evaluación y capas de almacenamiento.
Compatible con pytest y ejecutable directamente con Python estándar.
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class TestTecnocracia(unittest.TestCase):

    def test_agent_definitions_and_prompts(self):
        """Valida que todos los ministros y el primer ministro estén definidos con instrucciones rigurosas."""
        from primer_ministro.agent import root_agent, INSTRUCCION_PRIME_MINISTER
        from ministros.economia import ministro_economia, INSTRUCCION_ECONOMIA
        from ministros.educacion import ministro_educacion, INSTRUCCION_EDUCACION
        from ministros.interior import ministro_interior, INSTRUCCION_INTERIOR

        self.assertEqual(root_agent.name, "primer_ministro")
        self.assertEqual(len(root_agent.sub_agents), 3)
        self.assertIn("ADAPTABILIDAD", INSTRUCCION_PRIME_MINISTER)

        self.assertEqual(ministro_economia.name, "ministro_economia")
        self.assertEqual(len(ministro_economia.tools), 3)

        self.assertEqual(ministro_educacion.name, "ministro_educacion")
        self.assertEqual(len(ministro_educacion.tools), 3)

        self.assertEqual(ministro_interior.name, "ministro_interior")
        self.assertEqual(len(ministro_interior.tools), 3)

    def test_eval_sets_schema(self):
        """Valida la integridad de los conjuntos de evaluación de Google ADK."""
        eval_files = [
            ROOT_DIR / "primer_ministro" / "eval_set_1.evalset.json",
            ROOT_DIR / "primer_ministro" / "evals_primer_ministro.json"
        ]

        for eval_file in eval_files:
            self.assertTrue(eval_file.exists(), f"Fichero de evaluación {eval_file} no encontrado.")
            with open(eval_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertTrue("eval_cases" in data or "eval_set_id" in data)

    def test_storage_hybrid_fallback(self):
        """Valida que la capa de persistencia funcione correctamente en modo local."""
        import storage

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_json = Path(tmp_dir) / "test_datos_comunidad.json"
            orig_path = storage.RUTA_COMUNIDAD_LOCAL
            orig_use = storage.USE_FIRESTORE
            orig_client = storage._firestore_client
            orig_init = storage._firestore_initialized

            try:
                storage.RUTA_COMUNIDAD_LOCAL = test_json
                storage.USE_FIRESTORE = "false"
                storage._firestore_client = None
                storage._firestore_initialized = True

                # 1. Carga inicial
                datos = storage.cargar_datos_comunidad()
                self.assertEqual(datos["votos"]["positivos"], 0)
                self.assertEqual(datos["votos"]["negativos"], 0)
                self.assertEqual(len(datos["opiniones"]), 0)

                # 2. Registro de votos
                datos = storage.registrar_voto(True)
                self.assertEqual(datos["votos"]["positivos"], 1)
                datos = storage.registrar_voto(False)
                self.assertEqual(datos["votos"]["negativos"], 1)

                # 3. Registro de opinión
                nueva_op = {"autor": "Tester", "mensaje": "Test exitoso", "fecha": "17/09/2026"}
                datos = storage.agregar_opinion(nueva_op)
                self.assertEqual(len(datos["opiniones"]), 1)
                self.assertEqual(datos["opiniones"][0]["autor"], "Tester")

                # 4. Registro en historial
                nueva_conv = {
                    "tipo": "Consulta",
                    "agente": "Primer Ministro",
                    "pregunta": "¿Cómo reducir el déficit?",
                    "respuesta": "Aplicando optimización del gasto.",
                    "fecha": "17/09/2026",
                    "telemetria": {"duracion": 1.2}
                }
                datos = storage.agregar_conversacion_al_historial(nueva_conv)
                self.assertEqual(len(datos["historial_conversaciones"]), 1)

                # 5. Vaciar historial
                datos = storage.vaciar_historial_conversaciones()
                self.assertEqual(len(datos["historial_conversaciones"]), 0)

            finally:
                storage.RUTA_COMUNIDAD_LOCAL = orig_path
                storage.USE_FIRESTORE = orig_use
                storage._firestore_client = orig_client
                storage._firestore_initialized = orig_init

    def test_secrets_manager_fallback(self):
        """Valida la recuperación de secretos con fallback local."""
        import secrets_manager

        os.environ["GEMINI_API_KEY"] = "test-api-key-12345"
        secrets_manager._CACHE_SECRETS.clear()

        key = secrets_manager.get_gemini_api_key()
        self.assertEqual(key, "test-api-key-12345")

        info = secrets_manager.get_secrets_backend_info()
        self.assertEqual(info["estado"], "activa")


if __name__ == "__main__":
    unittest.main(verbosity=2)
