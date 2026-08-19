"""Resuelve la entrada del usuario a un directorio local analizable.

Acepta una ruta del disco o una URL de repositorio. En el segundo caso hace un
clon superficial (--depth 1) a un directorio temporal que se limpia al salir.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

CLONE_TIMEOUT_SECONDS = 180

# git@host:user/repo.git | https://host/user/repo(.git) | ssh://...
_SSH_RE = re.compile(r"^[\w.+-]+@[\w.-]+:[\w./~-]+$")
_URL_RE = re.compile(r"^(https?|git|ssh)://", re.IGNORECASE)
_SHORTHAND_RE = re.compile(r"^(github|gitlab)\.com/[\w.-]+/[\w.-]+/?$", re.IGNORECASE)


class SourceError(RuntimeError):
    """La fuente no se pudo resolver (ruta inexistente, clon fallido...)."""


@dataclass(slots=True)
class ResolvedSource:
    """Un proyecto listo para escanear."""

    path: Path
    kind: str  # "local" | "git"
    display: str  # lo que escribio el usuario
    name: str  # nombre inferido del proyecto
    _temp_dir: str | None = None

    def cleanup(self) -> None:
        """Borra el clon temporal, si lo hubo. Idempotente."""
        if self._temp_dir:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None

    def __enter__(self) -> ResolvedSource:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.cleanup()


def looks_like_repo_url(spec: str) -> bool:
    """True si la cadena parece una URL de repositorio y no una ruta local."""
    spec = spec.strip()
    return bool(
        _URL_RE.match(spec)
        or _SSH_RE.match(spec)
        or _SHORTHAND_RE.match(spec)
        or spec.endswith(".git")
    )


def _repo_name(url: str) -> str:
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return tail[:-4] if tail.endswith(".git") else tail or "repositorio"


def resolve_source(spec: str) -> ResolvedSource:
    """Convierte `spec` en un :class:`ResolvedSource`.

    Usalo como context manager para que el clon temporal se limpie solo.
    """
    spec = spec.strip().strip('"').strip("'")
    if not spec:
        raise SourceError("No se indico ninguna fuente a analizar.")

    if looks_like_repo_url(spec):
        return _clone(spec)

    path = Path(spec).expanduser().resolve()
    if not path.exists():
        raise SourceError(f"La ruta no existe: {path}")
    if not path.is_dir():
        raise SourceError(f"La ruta no es un directorio: {path}")
    return ResolvedSource(path=path, kind="local", display=str(path), name=path.name)


def _clone(url: str) -> ResolvedSource:
    if shutil.which("git") is None:
        raise SourceError("Git no esta instalado: no se puede clonar un repositorio remoto.")

    if _SHORTHAND_RE.match(url):
        url = f"https://{url.rstrip('/')}"

    temp_dir = tempfile.mkdtemp(prefix="classicalpy-")
    target = Path(temp_dir) / _repo_name(url)

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(target)],
            check=True,
            capture_output=True,
            text=True,
            timeout=CLONE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise SourceError(f"El clon supero los {CLONE_TIMEOUT_SECONDS}s: {url}") from exc
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        detail = (exc.stderr or "").strip().splitlines()
        raise SourceError(
            f"No se pudo clonar {url}: {detail[-1] if detail else 'error desconocido'}"
        ) from exc

    return ResolvedSource(
        path=target, kind="git", display=url, name=_repo_name(url), _temp_dir=temp_dir
    )
