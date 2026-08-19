"""Lectura de ficheros declarativos de dependencias.

Cada ecosistema declara sus dependencias de forma distinta. Aqui normalizamos
todos a la misma estructura :class:`Manifest` para que el resto del pipeline no
tenga que saber si el proyecto es Node, Python, PHP, Go o Rust.

Los parsers nunca lanzan: un manifiesto corrupto degrada el informe, no lo rompe.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from classicalpy.models import Manifest

# Fichero -> (ecosistema, parser). El orden define la prioridad de deteccion.
MANIFEST_FILES: tuple[str, ...] = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "composer.json",
    "go.mod",
    "Cargo.toml",
    "Gemfile",
    "pom.xml",
    "build.gradle",
)


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def parse_package_json(path: Path, rel: str) -> Manifest | None:
    raw = _read(path)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    def _deps(key: str) -> dict[str, str]:
        value = data.get(key)
        return {str(k): str(v) for k, v in value.items()} if isinstance(value, dict) else {}

    scripts = data.get("scripts")
    return Manifest(
        path=rel,
        ecosystem="node",
        project_name=data.get("name"),
        version=data.get("version"),
        description=data.get("description"),
        dependencies={**_deps("dependencies"), **_deps("peerDependencies")},
        dev_dependencies=_deps("devDependencies"),
        scripts={str(k): str(v) for k, v in scripts.items()} if isinstance(scripts, dict) else {},
    )


# "fastapi>=0.110,<1" / "uvicorn[standard]>=0.27" -> ("fastapi", ">=0.110,<1")
_REQ_RE = re.compile(r"^\s*([A-Za-z0-9._-]+)\s*(?:\[[^\]]*\])?\s*(.*)$")


def _split_requirement(spec: str) -> tuple[str, str] | None:
    spec = spec.split("#", 1)[0].split(";", 1)[0].strip()
    if not spec or spec.startswith("-"):  # -r otros.txt, --index-url, etc.
        return None
    match = _REQ_RE.match(spec)
    if match is None:
        return None
    return match.group(1), match.group(2).strip() or "*"


def parse_pyproject(path: Path, rel: str) -> Manifest | None:
    raw = _read(path)
    if raw is None:
        return None
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError:
        return None

    project = data.get("project", {}) if isinstance(data.get("project"), dict) else {}
    deps: dict[str, str] = {}
    for spec in project.get("dependencies", []) or []:
        if isinstance(spec, str) and (parsed := _split_requirement(spec)):
            deps[parsed[0]] = parsed[1]

    dev: dict[str, str] = {}
    optional = project.get("optional-dependencies")
    if isinstance(optional, dict):
        for group in optional.values():
            for spec in group or []:
                if isinstance(spec, str) and (parsed := _split_requirement(spec)):
                    dev[parsed[0]] = parsed[1]

    # Poetry declara sus dependencias en otro sitio.
    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
    if isinstance(poetry, dict):
        for name, constraint in (poetry.get("dependencies") or {}).items():
            if name.lower() != "python":
                deps[name] = constraint if isinstance(constraint, str) else "*"
        poetry_dev = poetry.get("group", {}).get("dev", {}).get("dependencies") or {}
        for name, constraint in poetry_dev.items():
            dev[name] = constraint if isinstance(constraint, str) else "*"

    scripts = project.get("scripts")
    return Manifest(
        path=rel,
        ecosystem="python",
        project_name=project.get("name") or poetry.get("name"),
        version=project.get("version") or poetry.get("version"),
        description=project.get("description") or poetry.get("description"),
        dependencies=deps,
        dev_dependencies=dev,
        scripts={str(k): str(v) for k, v in scripts.items()} if isinstance(scripts, dict) else {},
    )


def parse_requirements(path: Path, rel: str) -> Manifest | None:
    raw = _read(path)
    if raw is None:
        return None
    deps = {}
    for line in raw.splitlines():
        if parsed := _split_requirement(line):
            deps[parsed[0]] = parsed[1]
    # Un requirements-dev.txt describe herramientas, no la aplicacion.
    is_dev = any(marker in rel.lower() for marker in ("dev", "test", "lint"))
    return Manifest(
        path=rel,
        ecosystem="python",
        dependencies={} if is_dev else deps,
        dev_dependencies=deps if is_dev else {},
    )


def parse_composer(path: Path, rel: str) -> Manifest | None:
    raw = _read(path)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return Manifest(
        path=rel,
        ecosystem="php",
        project_name=data.get("name"),
        description=data.get("description"),
        dependencies={k: str(v) for k, v in (data.get("require") or {}).items() if k != "php"},
        dev_dependencies={k: str(v) for k, v in (data.get("require-dev") or {}).items()},
    )


# require github.com/gin-gonic/gin v1.9.1
_GOMOD_REQUIRE = re.compile(r"^\s*(?:require\s+)?([\w.\-/]+\.[\w.\-/]+)\s+(v[\w.\-+]+)")


def parse_go_mod(path: Path, rel: str) -> Manifest | None:
    raw = _read(path)
    if raw is None:
        return None
    name = None
    deps: dict[str, str] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("module "):
            name = stripped.removeprefix("module ").strip()
        elif match := _GOMOD_REQUIRE.match(line):
            deps[match.group(1)] = match.group(2)
    return Manifest(path=rel, ecosystem="go", project_name=name, dependencies=deps)


def parse_cargo(path: Path, rel: str) -> Manifest | None:
    raw = _read(path)
    if raw is None:
        return None
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError:
        return None

    def _flatten(table: object) -> dict[str, str]:
        if not isinstance(table, dict):
            return {}
        out = {}
        for name, constraint in table.items():
            if isinstance(constraint, str):
                out[name] = constraint
            elif isinstance(constraint, dict):
                out[name] = str(constraint.get("version", "*"))
        return out

    package = data.get("package", {}) if isinstance(data.get("package"), dict) else {}
    return Manifest(
        path=rel,
        ecosystem="rust",
        project_name=package.get("name"),
        version=package.get("version") if isinstance(package.get("version"), str) else None,
        description=package.get("description"),
        dependencies=_flatten(data.get("dependencies")),
        dev_dependencies=_flatten(data.get("dev-dependencies")),
    )


# gem "rails", "~> 7.0"
_GEM_RE = re.compile(r"""^\s*gem\s+["']([\w.\-]+)["'](?:\s*,\s*["']([^"']+)["'])?""")


def parse_gemfile(path: Path, rel: str) -> Manifest | None:
    raw = _read(path)
    if raw is None:
        return None
    deps = {}
    for line in raw.splitlines():
        if match := _GEM_RE.match(line):
            deps[match.group(1)] = match.group(2) or "*"
    return Manifest(path=rel, ecosystem="ruby", dependencies=deps)


def parse_generic_jvm(path: Path, rel: str) -> Manifest | None:
    """pom.xml y build.gradle: solo registramos presencia y artefactos evidentes."""
    raw = _read(path)
    if raw is None:
        return None
    deps = {a: "*" for a in re.findall(r"<artifactId>([\w.\-]+)</artifactId>", raw)}
    deps.update({m: "*" for m in re.findall(r"""["']([\w.\-]+:[\w.\-]+):[\w.\-]+["']""", raw)})
    return Manifest(path=rel, ecosystem="java", dependencies=deps)


_PARSERS = {
    "package.json": parse_package_json,
    "pyproject.toml": parse_pyproject,
    "requirements.txt": parse_requirements,
    "composer.json": parse_composer,
    "go.mod": parse_go_mod,
    "cargo.toml": parse_cargo,
    "gemfile": parse_gemfile,
    "pom.xml": parse_generic_jvm,
    "build.gradle": parse_generic_jvm,
}


def collect_manifests(root: Path, file_paths: list[str]) -> list[Manifest]:
    """Parsea todos los manifiestos encontrados en el inventario de ficheros.

    Ordena los de la raiz primero: en un monorepo, el manifiesto raiz es el que
    mejor describe el proyecto en conjunto.
    """
    found: list[Manifest] = []
    for rel in file_paths:
        filename = rel.rsplit("/", 1)[-1].lower()
        # requirements-dev.txt, requirements/base.txt... tambien cuentan.
        key = filename if filename in _PARSERS else None
        if key is None and filename.startswith("requirements") and filename.endswith(".txt"):
            key = "requirements.txt"
        if key is None:
            continue
        if (manifest := _PARSERS[key](root / rel, rel)) is not None:
            found.append(manifest)

    found.sort(key=lambda m: (m.path.count("/"), m.path))
    return found
