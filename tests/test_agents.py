"""
Tests unitarios para la estructura de agentes del gobierno tecnocrático.
Estos tests no requieren llamadas a la API de Gemini externa (coste cero, CI rápido).
"""
import pytest
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

def test_primer_ministro_estructura():
    """Valida la configuración del agente coordinador y sus subagentes."""
    assert root_agent.name == "primer_ministro"
    assert len(root_agent.sub_agents) == 3
    sub_names = [agent.name for agent in root_agent.sub_agents]
    assert "ministro_economia" in sub_names
    assert "ministro_educacion" in sub_names
    assert "ministro_interior" in sub_names
    assert "tecnocrático" in INSTRUCCION_PRIME_MINISTER.lower()

def test_herramientas_economia():
    """Valida que las herramientas de economía retornen cadenas válidas."""
    res_ipc = obtener_datos_ine("ipc")
    assert isinstance(res_ipc, str)
    assert "INE Oficial" in res_ipc

    res_paro = obtener_datos_ine("paro")
    assert isinstance(res_paro, str)
    assert "INE Oficial" in res_paro

    res_bde = obtener_datos_banco_espana("euribor")
    assert isinstance(res_bde, str)
    assert "Euríbor" in res_bde

    res_boe = consultar_boe_legislacion_fiscal("presupuestos")
    assert isinstance(res_boe, str)
    assert "BOE" in res_boe

def test_herramientas_educacion():
    """Valida que las herramientas de educación retornen cadenas válidas."""
    res_edu = obtener_datos_educacion_espana("gasto")
    assert isinstance(res_edu, str)
    assert "Ministerio de Educación" in res_edu

    res_eurostat = obtener_datos_eurostat_educacion("stem")
    assert isinstance(res_eurostat, str)
    assert "Eurostat" in res_eurostat

    res_uni = obtener_datos_universidades_siiu("fp")
    assert isinstance(res_uni, str)
    assert "SIIU" in res_uni

def test_herramientas_interior():
    """Valida que las herramientas de interior retornen cadenas válidas."""
    res_crim = obtener_datos_criminalidad_interior("ciber")
    assert isinstance(res_crim, str)
    assert "Ministerio del Interior" in res_crim

    res_aemet = obtener_datos_aemet_emergencias("avisos")
    assert isinstance(res_aemet, str)
    assert "Protección Civil" in res_aemet

    res_dgt = obtener_datos_dgt_trafico("seguridad")
    assert isinstance(res_dgt, str)
    assert "DGT" in res_dgt

def test_ministros_tools_registradas():
    """Valida que cada agente tenga sus herramientas registradas."""
    assert ministro_economia.tools is not None and len(ministro_economia.tools) >= 3
    assert ministro_educacion.tools is not None and len(ministro_educacion.tools) >= 3
    assert ministro_interior.tools is not None and len(ministro_interior.tools) >= 3
