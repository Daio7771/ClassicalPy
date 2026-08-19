"""Pruebas del pipeline completo sobre proyectos sinteticos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from classicalpy.models import FindingKind
from classicalpy.pipeline import analyze_directory
from classicalpy.report import render

# --------------------------------------------------------------- caso Next.js


def test_next_detecta_nombre_y_descripcion(proyecto_next: Path):
    informe = analyze_directory(proyecto_next)
    assert informe.project_name == "tienda-web"
    # Lo declarado por el equipo gana sobre lo deducido del vocabulario.
    assert "tienda en linea" in informe.domain.purpose.lower()
    assert informe.domain.confidence.value == "alta"


def test_next_detecta_arquitectura_ssr(proyecto_next: Path):
    informe = analyze_directory(proyecto_next)
    assert "Next.js" in informe.architecture.pattern
    assert informe.architecture.rationale, "el patron debe venir justificado"


def test_next_identifica_dominio_y_usuario(proyecto_next: Path):
    informe = analyze_directory(proyecto_next)
    # El vocabulario checkout/cart/product/order debe llevar a comercio.
    texto = f"{informe.domain.problem} {informe.domain.end_user}".lower()
    assert "compra" in texto or "pedido" in texto or "comercio" in texto


def test_next_stack_incluye_roles_no_vacios(proyecto_next: Path):
    informe = analyze_directory(proyecto_next)
    nombres = {t.name for t in informe.stack}
    assert {"next", "@prisma/client", "next-auth", "zod"} <= nombres
    assert all(t.role.strip() for t in informe.stack), "toda tecnologia debe tener rol explicado"


def test_next_flujo_incluye_auth_y_persistencia(proyecto_next: Path):
    informe = analyze_directory(proyecto_next)
    titulos = " ".join(s.title.lower() for s in informe.flow)
    assert "identidad" in titulos, "next-auth debe generar un paso de autenticacion"
    assert "consulta o modifica" in titulos, "Prisma debe generar un paso de persistencia"
    assert [s.order for s in informe.flow] == list(range(1, len(informe.flow) + 1))


def test_next_modulos_reconocen_convenciones(proyecto_next: Path):
    informe = analyze_directory(proyecto_next)
    roles = {m.path: m.role for m in informe.modules}
    assert roles.get("components") == "Componentes de UI"
    assert roles.get("services") == "Servicios"
    assert roles.get("app") == "Aplicacion / rutas"


def test_next_diagnostico_reconoce_fortalezas(proyecto_next: Path):
    informe = analyze_directory(proyecto_next)
    titulos = {f.title for f in informe.findings_of(FindingKind.FORTALEZA)}
    assert "Integracion continua configurada" in titulos
    assert any("prueba" in t.lower() for t in titulos)


def test_documentacion_larga_no_cuenta_como_fichero_grande(crear_proyecto):
    """Regresion: un README/documento de diseno extenso no es deuda tecnica.

    Detectado analizando un proyecto real cuyo resources/DESIGN-SYSTEM.md de
    800+ lineas aparecia como "fichero desproporcionadamente grande".
    """
    raiz = crear_proyecto(
        {
            "package.json": json.dumps({"name": "x", "dependencies": {"react": "^18"}}),
            "src/App.jsx": "export default () => null\n" * 10,
            "docs/DESIGN-SYSTEM.md": "# Seccion\ncontenido\n" * 500,
        }
    )
    informe = analyze_directory(raiz)
    assert not any("DESIGN-SYSTEM" in (f.evidence or "") for f in informe.findings)
    assert not any("grandes" in f.title.lower() for f in informe.findings)


# -------------------------------------------------------------- caso FastAPI


def test_fastapi_es_servicio_de_api(proyecto_fastapi: Path):
    informe = analyze_directory(proyecto_fastapi)
    assert "API" in informe.architecture.pattern
    assert informe.project_name == "facturacion-api"


def test_fastapi_detecta_riesgos_reales(proyecto_fastapi: Path):
    informe = analyze_directory(proyecto_fastapi)
    titulos = {f.title for f in informe.findings}
    assert "No hay pruebas automatizadas" in titulos
    assert "Sin integracion continua" in titulos
    assert "Sin README en la raiz" in titulos


def test_fastapi_usuario_final_sale_del_vocabulario(proyecto_fastapi: Path):
    """El vocabulario del dominio ('invoice') es mejor pista que la arquitectura."""
    informe = analyze_directory(proyecto_fastapi)
    assert "factur" in informe.domain.end_user.lower()


def test_usuario_final_cae_a_sistemas_sin_vocabulario(crear_proyecto):
    """Sin palabras de negocio reconocibles, una API se describe como consumida por sistemas."""
    raiz = crear_proyecto(
        {
            "pyproject.toml": '[project]\nname = "svc"\ndependencies = ["fastapi>=0.110"]\n',
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        }
    )
    informe = analyze_directory(raiz)
    assert "sistema" in informe.domain.end_user.lower()


# ------------------------------------------------------------ caso monolito


def test_backend_con_interfaz_propia_es_monolito(crear_proyecto):
    """Un servidor que sirve su propia UI no es ni API pura ni SPA."""
    raiz = crear_proyecto(
        {
            "pyproject.toml": '[project]\nname = "panel"\ndependencies = ["flask>=3.0"]\n',
            "app.py": "from flask import Flask\napp = Flask(__name__)\n" * 5,
            "templates/index.html": "<h1>Panel</h1>\n" * 4,
            "static/app.js": "console.log(1)\n" * 6,
        }
    )
    informe = analyze_directory(raiz)
    assert "Monolito" in informe.architecture.pattern

    # Y el flujo debe reflejar ese patron, no caer al generico.
    titulos = " ".join(s.title.lower() for s in informe.flow)
    assert "abre la aplicacion" in titulos
    assert "pinta el resultado" in titulos


def test_cada_patron_tiene_un_flujo_propio(proyecto_next, proyecto_fastapi, crear_proyecto):
    """Ningun patron reconocido debe caer en el flujo generico de respaldo."""
    spa = crear_proyecto(
        {
            "client/package.json": json.dumps({"name": "c", "dependencies": {"react": "^18"}}),
            "server/package.json": json.dumps({"name": "s", "dependencies": {"express": "^4"}}),
            "client/src/App.jsx": "export default () => null\n" * 5,
            "server/index.js": "require('express')()\n" * 5,
        }
    )
    for raiz in (proyecto_next, proyecto_fastapi, spa):
        informe = analyze_directory(raiz)
        titulos = {s.title for s in informe.flow}
        assert "Llega una peticion o invocacion" not in titulos, (
            f"{informe.architecture.pattern} cayo al flujo generico"
        )


# ------------------------------------------- regresiones sobre repos reales


def test_apps_anidado_no_convierte_en_monorepo(crear_proyecto):
    """Regresion: una carpeta 'apps/' dentro de un fixture de tests no es topologia.

    Detectado analizando pallets/flask, que tiene tests/test_apps/.../apps y era
    clasificado como monorepo por ello.
    """
    raiz = crear_proyecto(
        {
            "pyproject.toml": '[project]\nname = "lib"\ndependencies = ["flask>=3.0"]\n',
            "src/lib/__init__.py": "x = 1\n" * 20,
            "tests/test_apps/ejemplo/apps/uno/main.py": "x = 1\n" * 5,
            "tests/test_apps/ejemplo/apps/dos/main.py": "x = 1\n" * 5,
        }
    )
    informe = analyze_directory(raiz)
    assert "Monorepo" not in informe.architecture.pattern


def test_packages_en_raiz_si_es_monorepo(crear_proyecto):
    """El contraste del test anterior: en primer nivel si cuenta."""
    raiz = crear_proyecto(
        {
            "package.json": json.dumps({"name": "raiz", "workspaces": ["packages/*"]}),
            "pnpm-workspace.yaml": "packages:\n  - packages/*\n",
            "packages/ui/package.json": json.dumps({"name": "ui"}),
            "packages/ui/src/index.ts": "export const a = 1\n" * 5,
            "packages/api/package.json": json.dumps({"name": "api"}),
            "packages/api/src/index.ts": "export const b = 1\n" * 5,
        }
    )
    informe = analyze_directory(raiz)
    assert "Monorepo" in informe.architecture.pattern


def test_monorepo_hereda_el_flujo_de_su_stack(crear_proyecto):
    """Un monorepo no tiene flujo propio: debe tomar el del stack que contiene."""
    raiz = crear_proyecto(
        {
            "pnpm-workspace.yaml": "packages:\n  - packages/*\n",
            "package.json": json.dumps({"name": "raiz"}),
            "packages/web/package.json": json.dumps(
                {"name": "web", "dependencies": {"next": "14.0.0", "react": "^18"}}
            ),
            "packages/web/app/page.tsx": "export default () => null\n" * 5,
        }
    )
    informe = analyze_directory(raiz)
    assert "Monorepo" in informe.architecture.pattern
    titulos = {s.title for s in informe.flow}
    assert "Llega una peticion o invocacion" not in titulos
    assert any("Next.js" in s.title for s in informe.flow)


# ------------------------------------------------------------ degradacion


def test_proyecto_vacio_no_revienta(proyecto_vacio: Path):
    informe = analyze_directory(proyecto_vacio)
    assert informe.stats.total_files == 0
    assert informe.warnings, "debe avisar de que no encontro nada"
    assert informe.pitch, "aun sin datos debe producir un texto"


def test_proyecto_inexistente_da_error_claro():
    from classicalpy.ingest.source import SourceError, resolve_source

    with pytest.raises(SourceError, match="no existe"):
        resolve_source("./ruta/que/no/existe/jamas")


# ---------------------------------------------------------------- renderers


@pytest.mark.parametrize("formato", ["markdown", "json", "texto"])
def test_todos_los_formatos_producen_salida(proyecto_next: Path, formato: str):
    salida = render(analyze_directory(proyecto_next), formato)
    assert len(salida) > 500


def test_markdown_contiene_las_cinco_secciones(proyecto_next: Path):
    md = render(analyze_directory(proyecto_next), "markdown")
    for seccion in (
        "Explicacion en 5 segundos",
        "Ficha Tecnica y Arquitectura",
        "Flujo de Trabajo Principal",
        "Mapa Conceptual de Modulos",
        "Diagnostico del Codigo",
    ):
        assert seccion in md, f"falta la seccion: {seccion}"


def test_json_es_serializable_y_completo(proyecto_next: Path):
    datos = json.loads(render(analyze_directory(proyecto_next), "json"))
    assert datos["project_name"] == "tienda-web"
    assert datos["stack"] and datos["flow"] and datos["modules"] and datos["findings"]
    # Los Enum deben salir como texto plano, no como repr de Python.
    assert datos["domain"]["confidence"] in {"alta", "media", "baja"}


def test_markdown_escapa_pipes_en_la_tabla(crear_proyecto):
    raiz = crear_proyecto(
        {"package.json": json.dumps({"name": "x", "dependencies": {"react": "^18"}})}
    )
    md = render(analyze_directory(raiz), "markdown")
    # Cada fila de la tabla debe tener exactamente 5 separadores (4 columnas).
    filas = [ln for ln in md.splitlines() if ln.startswith("| **")]
    assert filas
    for fila in filas:
        assert fila.count("|") - fila.count("\\|") == 5, f"fila mal formada: {fila}"


# ---------------------------------------------------------- seguridad: symlinks


def test_symlink_a_fichero_externo_no_se_lee(tmp_path: Path):
    """Un repositorio ajeno no debe poder exfiltrar ficheros del host via symlinks.

    README.md -> /ruta/fuera/del/proyecto no debe aparecer en el inventario, y su
    contenido (el del fichero externo) nunca debe llegar al informe.
    """
    secreto = tmp_path / "secreto.txt"
    secreto.write_text("CONTENIDO_SECRETO_DEL_HOST\n", encoding="utf-8")

    raiz = tmp_path / "repo-ajeno"
    raiz.mkdir()
    (raiz / "package.json").write_text('{"name": "x"}', encoding="utf-8")
    try:
        (raiz / "README.md").symlink_to(secreto)
    except OSError:
        pytest.skip("el entorno no permite crear symlinks (falta privilegio en Windows)")

    informe = analyze_directory(raiz)
    assert "CONTENIDO_SECRETO_DEL_HOST" not in render(informe, "markdown")
    assert "CONTENIDO_SECRETO_DEL_HOST" not in render(informe, "json")
    assert informe.stats.total_files == 1  # solo package.json: el symlink no se cuenta


# --------------------------------------------------------- seguridad: fuentes


def test_esquemas_peligrosos_no_se_tratan_como_repositorio():
    from classicalpy.ingest.source import looks_like_repo_url

    # ssh:// y git:// ya no se aceptan: van directos a un `ssh`/socket real
    # sin que validemos el host antes.
    assert not looks_like_repo_url("ssh://git@github.com/x/y.git")
    assert not looks_like_repo_url("git://github.com/x/y.git")
    assert not looks_like_repo_url("git@github.com:x/y.git")
    # Un host que empiece por '-' inyectaria flags a `ssh` (CVE-2017-1000117).
    assert not looks_like_repo_url("ssh://-oProxyCommand=touch%20pwned/x")


def test_https_sigue_aceptado_como_repositorio():
    from classicalpy.ingest.source import looks_like_repo_url

    assert looks_like_repo_url("https://github.com/pallets/flask")
    assert looks_like_repo_url("github.com/pallets/flask")


def test_clonar_hacia_host_interno_se_rechaza():
    from classicalpy.ingest.source import SourceError, resolve_source

    for objetivo in (
        "https://localhost/x.git",
        "https://127.0.0.1/x.git",
        "https://169.254.169.254/latest/meta-data/",  # metadatos de nube
        "https://10.0.0.5/x.git",
        "https://192.168.1.1/x.git",
    ):
        with pytest.raises(SourceError, match="no se permite|interna|local"):
            resolve_source(objetivo)


# ------------------------------------------------------------- seguridad: CLI


def test_servir_rechaza_host_publico_sin_solo_repos(monkeypatch):
    from classicalpy.cli import main

    monkeypatch.delenv("CLASSICALPY_SOLO_REPOS", raising=False)
    codigo = main(["servir", "--host", "0.0.0.0"])
    assert codigo == 1


def test_servir_permite_host_publico_con_solo_repos(monkeypatch):
    """Con SOLO_REPOS activo, la puerta de seguridad debe dejar pasar sin bloquear."""
    pytest.importorskip("uvicorn", reason="requiere el extra 'web'")
    import uvicorn

    from classicalpy.cli import main

    monkeypatch.setenv("CLASSICALPY_SOLO_REPOS", "1")
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: None)
    assert main(["servir", "--host", "0.0.0.0"]) == 0


def test_servir_permite_host_publico_con_override_explicito(monkeypatch):
    """El flag explicito tambien debe dejar pasar la puerta de seguridad."""
    pytest.importorskip("uvicorn", reason="requiere el extra 'web'")
    import uvicorn

    from classicalpy.cli import main

    monkeypatch.delenv("CLASSICALPY_SOLO_REPOS", raising=False)
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: None)
    assert main(["servir", "--host", "0.0.0.0", "--permitir-analisis-local-publico"]) == 0


def test_dominio_publico_con_prefijo_numerico_no_se_bloquea():
    """Regresion: un dominio como '10.example.com' no es la IP 10.x.x.x.

    El primer bloqueo por prefijo de texto bloqueaba por error cualquier
    dominio que empezara con esos digitos, no solo direcciones IP reales.
    """
    from classicalpy.ingest.source import _es_host_prohibido

    for host in ("10.example.com", "192.168.example.org", "172.16.mi-empresa.com"):
        assert not _es_host_prohibido(host), f"{host} es un dominio, no deberia bloquearse"

    for host in ("10.0.0.1", "192.168.1.1", "172.16.0.1", "127.0.0.1", "169.254.1.1", "localhost"):
        assert _es_host_prohibido(host), f"{host} es una IP privada/local y debe bloquearse"
