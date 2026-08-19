"""Pruebas de la API HTTP. Se saltan si el extra `web` no esta instalado."""

from __future__ import annotations

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="requiere el extra 'web'")
from fastapi.testclient import TestClient  # noqa: E402

from classicalpy.web.app import app  # noqa: E402


@pytest.fixture
def cliente() -> TestClient:
    return TestClient(app)


def test_salud(cliente: TestClient):
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


def test_index_sirve_la_interfaz(cliente: TestClient):
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "ClassicalPy" in respuesta.text


def test_estaticos_disponibles(cliente: TestClient):
    for recurso in ("/estatico/estilos.css", "/estatico/app.js"):
        assert cliente.get(recurso).status_code == 200, recurso


def test_analizar_devuelve_informe_json(cliente: TestClient, proyecto_next: Path):
    respuesta = cliente.post("/api/analizar", json={"fuente": str(proyecto_next)})
    assert respuesta.status_code == 200

    datos = respuesta.json()
    assert datos["project_name"] == "tienda-web"
    assert datos["stack"] and datos["flow"] and datos["modules"]
    assert "Next.js" in datos["architecture"]["pattern"]


def test_analizar_en_markdown(cliente: TestClient, proyecto_fastapi: Path):
    respuesta = cliente.post(
        "/api/analizar", json={"fuente": str(proyecto_fastapi), "formato": "markdown"}
    )
    assert respuesta.status_code == 200
    assert "Ficha Tecnica" in respuesta.text


def test_fuente_inexistente_da_400(cliente: TestClient):
    respuesta = cliente.post("/api/analizar", json={"fuente": "/no/existe/en/ningun/sitio"})
    assert respuesta.status_code == 400
    assert "no existe" in respuesta.json()["detail"].lower()


def test_formato_invalido_da_422(cliente: TestClient, proyecto_fastapi: Path):
    respuesta = cliente.post(
        "/api/analizar", json={"fuente": str(proyecto_fastapi), "formato": "pdf"}
    )
    assert respuesta.status_code == 422


def test_fuente_vacia_es_rechazada(cliente: TestClient):
    assert cliente.post("/api/analizar", json={"fuente": ""}).status_code == 422


def test_modo_solo_repos_bloquea_rutas_locales(monkeypatch, proyecto_fastapi: Path):
    """Con CLASSICALPY_SOLO_REPOS la API no debe leer el disco del servidor."""
    import classicalpy.web.app as modulo

    monkeypatch.setattr(modulo, "SOLO_REPOS", True)
    cliente = TestClient(modulo.app)

    respuesta = cliente.post("/api/analizar", json={"fuente": str(proyecto_fastapi)})
    assert respuesta.status_code == 403

    # Una URL de repositorio si se acepta (falla despues, al clonar, no aqui).
    respuesta = cliente.post("/api/analizar", json={"fuente": "https://example.com/x/y.git"})
    assert respuesta.status_code != 403
