"""Paquete de Ministerios del Gobierno Tecnocrático."""
from .economia import ministro_economia
from .educacion import ministro_educacion
from .interior import ministro_interior

# Fallback por si adk web se abre apuntando a ministros
root_agent = ministro_economia

__all__ = ["ministro_economia", "ministro_educacion", "ministro_interior", "root_agent"]
