"""Recorre el arbol de ficheros y produce el inventario base del analisis.

Filtra ruido (dependencias instaladas, artefactos de build, binarios) para que
las metricas reflejen codigo escrito por el equipo, no codigo descargado.
"""

from __future__ import annotations

import os
from pathlib import Path

from classicalpy.models import FileInfo, ProjectStats

# Carpetas que nunca son codigo del proyecto: dependencias, builds, caches, IDE.
IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git", ".hg", ".svn", ".idea", ".vscode", ".vs",
        "node_modules", "bower_components", "jspm_packages", "vendor", "Pods",
        "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
        ".venv", "venv", "env", ".env.d", "site-packages",
        "dist", "build", "out", "target", "bin", "obj", "_build",
        ".next", ".nuxt", ".svelte-kit", ".astro", ".output", ".parcel-cache",
        ".cache", ".turbo", ".gradle", ".terraform", ".serverless",
        "coverage", "htmlcov", ".nyc_output",
        ".classicalpy-cache",
    }
)

# Extension -> lenguaje legible. El orden no importa, es un lookup.
LANGUAGE_BY_EXT: dict[str, str] = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript", ".tsx": "TypeScript",
    ".vue": "Vue", ".svelte": "Svelte", ".astro": "Astro",
    ".html": "HTML", ".htm": "HTML", ".ejs": "HTML", ".hbs": "HTML",
    ".jinja": "HTML", ".jinja2": "HTML", ".j2": "HTML", ".twig": "HTML", ".blade.php": "HTML",
    ".css": "CSS", ".scss": "CSS", ".sass": "CSS", ".less": "CSS", ".styl": "CSS",
    ".php": "PHP", ".rb": "Ruby", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".cs": "C#", ".c": "C", ".h": "C", ".cpp": "C++", ".hpp": "C++", ".cc": "C++",
    ".swift": "Swift", ".dart": "Dart", ".ex": "Elixir", ".exs": "Elixir",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".ps1": "PowerShell",
    ".sql": "SQL", ".prisma": "Schema", ".graphql": "GraphQL", ".gql": "GraphQL",
    ".proto": "Protobuf",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML",
    ".ini": "Config", ".cfg": "Config", ".conf": "Config", ".env": "Config",
    ".xml": "XML", ".md": "Markdown", ".mdx": "Markdown", ".rst": "Markdown",
    ".txt": "Texto",
}

# Ficheros sin extension util que si son configuracion relevante.
CONFIG_FILENAMES: frozenset[str] = frozenset(
    {
        "dockerfile", "docker-compose.yml", "docker-compose.yaml", "makefile",
        "procfile", "vagrantfile", "jenkinsfile", ".gitignore", ".dockerignore",
        ".editorconfig", ".gitattributes", ".nvmrc", ".python-version",
    }
)

CONFIG_LANGUAGES: frozenset[str] = frozenset({"JSON", "YAML", "TOML", "Config", "XML"})

# Marcas que identifican un fichero como test, en ruta o en nombre.
TEST_PATH_MARKERS: tuple[str, ...] = ("/test/", "/tests/", "/__tests__/", "/spec/", "/e2e/")
TEST_NAME_MARKERS: tuple[str, ...] = (
    ".test.", ".spec.", "_test.", "_spec.", "test_", "conftest.py",
)

MAX_FILE_BYTES = 2_000_000  # por encima de esto no contamos lineas (probable binario/bundle)


class Scanner:
    """Convierte un directorio en una lista de :class:`FileInfo` + estadisticas."""

    def __init__(self, root: Path, max_files: int = 20_000) -> None:
        self.root = Path(root).resolve()
        self.max_files = max_files
        self.warnings: list[str] = []

    def scan(self) -> tuple[list[FileInfo], ProjectStats]:
        files: list[FileInfo] = []
        stats = ProjectStats()
        truncated = False

        for dirpath, dirnames, filenames in os.walk(self.root):
            # Poda in-place: os.walk no desciende en lo que quitemos de dirnames.
            keep = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".egg-info")]
            stats.skipped_dirs += len(dirnames) - len(keep)
            dirnames[:] = sorted(keep)

            for filename in sorted(filenames):
                if len(files) >= self.max_files:
                    truncated = True
                    break
                info = self._inspect(Path(dirpath) / filename)
                if info is not None:
                    files.append(info)
            if truncated:
                break

        if truncated:
            self.warnings.append(
                f"Proyecto muy grande: analisis truncado a {self.max_files} ficheros."
            )

        self._aggregate(files, stats)
        return files, stats

    def _inspect(self, path: Path) -> FileInfo | None:
        """Clasifica un fichero. Devuelve None si no aporta al analisis."""
        if path.is_symlink():
            # os.walk no sigue symlinks a directorios (followlinks=False), pero
            # SI lista y abriria un symlink a un fichero individual. Un repositorio
            # ajeno podria incluir p.ej. "README.md -> /etc/passwd" y su contenido
            # se filtraria en el informe (ver analyze/domain.py:_read_readme). No
            # se sigue jamas un enlace fuera del arbol que se pidio analizar.
            return None
        try:
            size = path.stat().st_size
        except OSError:
            return None

        rel = path.relative_to(self.root).as_posix()
        lower = path.name.lower()
        language = LANGUAGE_BY_EXT.get(path.suffix.lower())

        if language is None:
            if lower in CONFIG_FILENAMES:
                language = "Config"
            elif lower.startswith("dockerfile"):
                language = "Config"
            else:
                return None  # binario, imagen, lockfile exotico: fuera del inventario

        lines = self._count_lines(path) if size <= MAX_FILE_BYTES else 0
        rel_lower = "/" + rel.lower()

        return FileInfo(
            path=rel,
            size=size,
            lines=lines,
            language=language,
            is_test=(
                any(m in rel_lower for m in TEST_PATH_MARKERS)
                or any(m in lower for m in TEST_NAME_MARKERS)
            ),
            is_config=language in CONFIG_LANGUAGES,
        )

    @staticmethod
    def _count_lines(path: Path) -> int:
        try:
            with path.open("rb") as handle:
                chunk = handle.read(8192)
                if b"\x00" in chunk:  # NUL byte => binario disfrazado
                    return 0
                count = chunk.count(b"\n")
                while data := handle.read(1 << 20):
                    count += data.count(b"\n")
                return count + 1 if chunk else 0
        except OSError:
            return 0

    @staticmethod
    def _aggregate(files: list[FileInfo], stats: ProjectStats) -> None:
        for f in files:
            stats.total_files += 1
            stats.total_lines += f.lines
            stats.total_bytes += f.size
            stats.lines_by_language[f.language] = (
                stats.lines_by_language.get(f.language, 0) + f.lines
            )
            stats.files_by_language[f.language] = stats.files_by_language.get(f.language, 0) + 1
            if f.is_test:
                stats.test_files += 1
            if f.is_config:
                stats.config_files += 1

        # Un README o un documento de diseno largos no son deuda tecnica: son
        # prosa, no logica que alguien tenga que mantener o testear.
        code = [
            f for f in files
            if not f.is_config and f.lines > 0 and f.language not in {"Markdown", "Texto"}
        ]
        code.sort(key=lambda f: f.lines, reverse=True)
        stats.largest_files = [(f.path, f.lines) for f in code[:10]]
