"""ClassicalPy: analizador estatico de proyectos web.

Ingesta un proyecto (carpeta local o repositorio Git) y produce un informe de
arquitectura en cinco secciones, legible por perfiles tecnicos y no tecnicos.

Uso rapido:
    >>> from classicalpy import analizar
    >>> informe = analizar("./mi-proyecto")
    >>> print(informe.pitch)
"""

from classicalpy.models import ProjectReport

__version__ = "0.1.0"
__all__ = ["ProjectReport", "analizar", "__version__"]


def analizar(source: str) -> ProjectReport:
    """Analiza una ruta local o URL de repositorio y devuelve el informe."""
    from classicalpy.pipeline import run

    return run(source)
