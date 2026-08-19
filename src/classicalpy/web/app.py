"""API HTTP e interfaz web de ClassicalPy.

La API es la misma funcionalidad que la CLI, expuesta por HTTP. La interfaz
grafica es HTML/CSS/JS servido desde aqui, sin paso de build ni dependencias
de terceros: se abre y funciona.

AVISO DE SEGURIDAD
    El endpoint de analisis lee rutas del sistema de ficheros del servidor.
    Por eso la aplicacion escucha en 127.0.0.1 por defecto y esta pensada como
    herramienta local. Exponerla en una red publica permitiria a cualquiera
    leer la estructura de ficheros de la maquina; para ese caso hay que poner
    CLASSICALPY_SOLO_REPOS=1, que desactiva el analisis de rutas locales.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from classicalpy import __version__
from classicalpy.ingest.source import SourceError, looks_like_repo_url
from classicalpy.pipeline import run
from classicalpy.report import FORMATS, render

STATIC_DIR = Path(__file__).parent / "static"
SOLO_REPOS = os.getenv("CLASSICALPY_SOLO_REPOS", "").strip() in {"1", "true", "yes"}

app = FastAPI(
    title="ClassicalPy",
    version=__version__,
    description="Analiza un proyecto web y devuelve un informe de arquitectura.",
)


class PeticionAnalisis(BaseModel):
    """Cuerpo del POST /api/analizar."""

    fuente: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="Ruta local o URL de repositorio Git.",
        examples=["./mi-proyecto", "https://github.com/pallets/flask"],
    )
    formato: str = Field(
        default="json",
        description=f"Formato del informe. Opciones: {', '.join(FORMATS)}.",
    )
    max_ficheros: int = Field(default=20_000, ge=1, le=200_000)


@app.get("/api/salud", tags=["sistema"])
def salud() -> dict[str, object]:
    """Comprobacion de vida y capacidades activas."""
    return {"estado": "ok", "version": __version__, "solo_repos": SOLO_REPOS}


@app.post("/api/analizar", tags=["analisis"])
def analizar(peticion: PeticionAnalisis):
    """Analiza el proyecto indicado y devuelve el informe."""
    if peticion.formato not in FORMATS:
        raise HTTPException(422, f"Formato no soportado. Opciones: {', '.join(FORMATS)}.")

    if SOLO_REPOS and not looks_like_repo_url(peticion.fuente):
        raise HTTPException(
            403,
            "Esta instancia solo acepta URLs de repositorio; el analisis de rutas locales "
            "esta desactivado (CLASSICALPY_SOLO_REPOS).",
        )

    try:
        informe = run(peticion.fuente, max_files=peticion.max_ficheros)
    except SourceError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # el analisis nunca debe tumbar el servidor
        raise HTTPException(500, f"El analisis fallo: {exc}") from exc

    if peticion.formato == "json":
        return informe.to_dict()
    return PlainTextResponse(render(informe, peticion.formato))


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/estatico", StaticFiles(directory=STATIC_DIR), name="estatico")
