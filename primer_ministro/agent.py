import os
import sys
from pathlib import Path
from dotenv import load_dotenv

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

REGLA DE ADAPTABILIDAD INTELIGENTE:
- Si el ciudadano envía un saludo, agradecimiento o pregunta trivial/de cortesía (ej: "Hola", "Buenos días", "¿Para qué sirves?", "¿Quién eres?", "¿Qué haces?"):
  * NO generes informes largos ni estructuras complejas.
  * Responde de forma amable, cercana y breve (1 o 2 frases simples) explicando quién eres y ofreciéndote a ayudar.
- Si el ciudadano plantea un dilema, problema regional o consulta técnica real:
  * Dicta tu resolución estructurada con rigor técnico, medidas operativas y comunicado, delegando en tus ministros especializados.
"""

root_agent = Agent(
    name="primer_ministro",
    description="Primer Ministro y coordinador del gabinete del gobierno tecnocrático.",
    model=os.getenv("MODEL_NAME", "gemini-2.0-flash"),
    instruction=INSTRUCCION_PRIME_MINISTER,
    sub_agents=[ministro_economia, ministro_educacion, ministro_interior]
)
