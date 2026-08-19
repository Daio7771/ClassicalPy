"""Modelo de datos del informe.

Todo el pipeline (ingesta -> deteccion -> analisis -> reporte) se comunica
mediante estas estructuras. Son dataclasses de stdlib para que el nucleo
no arrastre dependencias.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Any


class Confidence(StrEnum):
    """Cuanta evidencia respalda una deduccion."""

    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class FindingKind(StrEnum):
    """Naturaleza de un hallazgo del diagnostico."""

    FORTALEZA = "fortaleza"
    MEJORA = "mejora"
    RIESGO = "riesgo"


@dataclass(slots=True)
class FileInfo:
    """Un fichero del proyecto, ya normalizado."""

    path: str  # relativo a la raiz, siempre con "/"
    size: int
    lines: int
    language: str
    is_test: bool = False
    is_config: bool = False

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def ext(self) -> str:
        name = self.name
        return name[name.rfind(".") :].lower() if "." in name[1:] else ""


@dataclass(slots=True)
class Manifest:
    """Un fichero declarativo de dependencias ya parseado."""

    path: str
    ecosystem: str  # node, python, php, go, rust, ruby, java, docker
    project_name: str | None = None
    version: str | None = None
    description: str | None = None
    dependencies: dict[str, str] = field(default_factory=dict)
    dev_dependencies: dict[str, str] = field(default_factory=dict)
    scripts: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TechEntry:
    """Una fila de la tabla Tecnologia | Rol en este proyecto."""

    name: str
    category: str
    role: str
    version: str | None = None
    ecosystem: str | None = None
    evidence: str | None = None


@dataclass(slots=True)
class ModuleNode:
    """Una carpeta clave y la responsabilidad que se le atribuye."""

    path: str
    role: str
    purpose: str
    file_count: int
    languages: list[str] = field(default_factory=list)
    key_files: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FlowStep:
    """Un paso del recorrido de una peticion de punta a punta."""

    order: int
    actor: str
    title: str
    detail: str
    evidence: str | None = None


@dataclass(slots=True)
class Finding:
    """Un punto critico: fortaleza, deuda tecnica o riesgo."""

    kind: FindingKind
    title: str
    detail: str
    evidence: str | None = None
    impact: str | None = None


@dataclass(slots=True)
class DomainGuess:
    """Deduccion de proposito, dominio y usuario final."""

    purpose: str
    problem: str
    end_user: str
    confidence: Confidence = Confidence.MEDIA
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ArchitectureGuess:
    """Patron arquitectonico inferido."""

    pattern: str
    rationale: list[str] = field(default_factory=list)
    confidence: Confidence = Confidence.MEDIA


@dataclass(slots=True)
class ProjectStats:
    """Metricas agregadas del escaneo."""

    total_files: int = 0
    total_lines: int = 0
    total_bytes: int = 0
    lines_by_language: dict[str, int] = field(default_factory=dict)
    files_by_language: dict[str, int] = field(default_factory=dict)
    test_files: int = 0
    config_files: int = 0
    largest_files: list[tuple[str, int]] = field(default_factory=list)
    skipped_dirs: int = 0

    @property
    def test_ratio(self) -> float:
        """Proporcion de ficheros de test sobre el total de codigo."""
        code = self.total_files - self.config_files
        return (self.test_files / code) if code > 0 else 0.0


@dataclass(slots=True)
class ProjectReport:
    """El informe completo. Es lo que serializan los renderers."""

    project_name: str
    source: str
    source_kind: str  # "local" | "git"
    generated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    pitch: str = ""
    domain: DomainGuess | None = None
    architecture: ArchitectureGuess | None = None
    stack: list[TechEntry] = field(default_factory=list)
    flow: list[FlowStep] = field(default_factory=list)
    modules: list[ModuleNode] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    stats: ProjectStats = field(default_factory=ProjectStats)
    warnings: list[str] = field(default_factory=list)

    def findings_of(self, kind: FindingKind) -> list[Finding]:
        return [f for f in self.findings if f.kind is kind]

    def to_dict(self) -> dict[str, Any]:
        """Serializa a JSON-compatible (los Enum se vuelven su valor str)."""

        def _clean(value: Any) -> Any:
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, dict):
                return {k: _clean(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [_clean(v) for v in value]
            return value

        data = _clean(asdict(self))
        data["stats"]["test_ratio"] = round(self.stats.test_ratio, 3)
        return data
