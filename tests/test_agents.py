"""
Tests unitarios para la estructura de agentes del gobierno tecnocrático.
Estos tests no requieren llamadas a la API de Gemini externa (coste cero, CI rápido).
"""
import unittest
from primer_ministro.agent import root_agent, INSTRUCCION_PRIME_MINISTER
from ministros.economia import (
    ministro_economia,
    obtener_datos_ine,
    obtener_datos_banco_espana,
    consultar_boe_legislacion_fiscal
)
from ministros.educacion import (
    ministro_educacion,
    obtener_datos_educacion_espana,
    obtener_datos_eurostat_educacion,
    obtener_datos_universidades_siiu
)
from ministros.interior import (
    ministro_interior,
    obtener_datos_criminalidad_interior,
    obtener_datos_aemet_emergencias,
    obtener_datos_dgt_trafico
)


class TestAgentsStructure(unittest.TestCase):

    def test_primer_ministro_estructura(self):
        """Valida la configuración del agente coordinador y sus subagentes."""
        self.assertEqual(root_agent.name, "primer_ministro")
        self.assertEqual(len(root_agent.sub_agents), 3)
        sub_names = [agent.name for agent in root_agent.sub_agents]
        self.assertIn("ministro_economia", sub_names)
        self.assertIn("ministro_educacion", sub_names)
        self.assertIn("ministro_interior", sub_names)
        self.assertIn("tecnocrático", INSTRUCCION_PRIME_MINISTER.lower())

    def test_herramientas_economia(self):
        """Valida que las herramientas de economía retornen cadenas válidas."""
        res_ipc = obtener_datos_ine("ipc")
        self.assertIsInstance(res_ipc, str)
        self.assertIn("INE Oficial", res_ipc)

        res_paro = obtener_datos_ine("paro")
        self.assertIsInstance(res_paro, str)
        self.assertIn("INE Oficial", res_paro)

        res_bde = obtener_datos_banco_espana("euribor")
        self.assertIsInstance(res_bde, str)
        self.assertIn("Euríbor", res_bde)

        res_boe = consultar_boe_legislacion_fiscal("presupuestos")
        self.assertIsInstance(res_boe, str)
        self.assertIn("BOE", res_boe)

    def test_herramientas_educacion(self):
        """Valida que las herramientas de educación retornen cadenas válidas."""
        res_edu = obtener_datos_educacion_espana("gasto")
        self.assertIsInstance(res_edu, str)
        self.assertIn("Ministerio de Educación", res_edu)

        res_eurostat = obtener_datos_eurostat_educacion("stem")
        self.assertIsInstance(res_eurostat, str)
        self.assertIn("Eurostat", res_eurostat)

        res_uni = obtener_datos_universidades_siiu("fp")
        self.assertIsInstance(res_uni, str)
        self.assertIn("SIIU", res_uni)

    def test_herramientas_interior(self):
        """Valida que las herramientas de interior retornen cadenas válidas."""
        res_crim = obtener_datos_criminalidad_interior("ciber")
        self.assertIsInstance(res_crim, str)
        self.assertIn("Ministerio del Interior", res_crim)

        res_aemet = obtener_datos_aemet_emergencias("avisos")
        self.assertIsInstance(res_aemet, str)
        self.assertIn("Protección Civil", res_aemet)

        res_dgt = obtener_datos_dgt_trafico("seguridad")
        self.assertIsInstance(res_dgt, str)
        self.assertIn("DGT", res_dgt)

    def test_ministros_tools_registradas(self):
        """Valida que cada agente tenga sus herramientas registradas."""
        self.assertIsNotNone(ministro_economia.tools)
        self.assertGreaterEqual(len(ministro_economia.tools), 3)
        self.assertIsNotNone(ministro_educacion.tools)
        self.assertGreaterEqual(len(ministro_educacion.tools), 3)
        self.assertIsNotNone(ministro_interior.tools)
        self.assertGreaterEqual(len(ministro_interior.tools), 3)


if __name__ == "__main__":
    unittest.main()
