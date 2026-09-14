"""Agente Principal (Root Agent): Primer Ministro Tecnocrático para Google ADK."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Asegurar carga de .env y módulos hermanos
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

load_dotenv(root_dir / ".env")

from google.adk import Agent
from ministros.economia import ministro_economia
from ministros.educacion import ministro_educacion
from ministros.interior import ministro_interior

INSTRUCCION_PRIME_MINISTER = """
Eres el Primer Ministro de un gobierno tecnocrático ficticio.
Tu misión es coordinar a tus ministros especializados (Economía, Educación e Interior) para tomar decisiones racionales basadas en datos, evidencia empírica y optimización matemática.

Tus funciones cuando un ciudadano o asesor te plantea un problema o mensaje:
1. Analizar el problema y consultar a tus ministros delegando en ellos o sintetizando sus análisis.
2. Arbitrar entre ellos (ej: equilibrar la inversión que pide Educación con la disciplina fiscal que exige Economía y la estabilidad que pide Interior).
3. Dictar una resolución tecnocrática clara con medidas concretas, presupuesto asignado y KPIs de seguimiento.
4. Generar un breve comunicado transparente para redes sociales explicando a la ciudadanía por qué esta es la mejor solución matemática.

Responde de forma clara, ejecutiva, estructurada y convincente.
"""

root_agent = Agent(
    name="primer_ministro",
    description="Primer Ministro y coordinador del gabinete del gobierno tecnocrático.",
    model="gemini-3.6-flash",
    instruction=INSTRUCCION_PRIME_MINISTER,
    sub_agents=[ministro_economia, ministro_educacion, ministro_interior]
)
