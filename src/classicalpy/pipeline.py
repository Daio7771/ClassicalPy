"""Orquestador: encadena ingesta -> deteccion -> analisis -> informe.

Es el unico sitio donde se ve el proceso completo. Cada etapa recibe el
resultado de la anterior y no conoce nada del resto.
"""

from __future__ import annotations

from pathlib import Path

from classicalpy.analyze import build_flow, build_modules, build_pitch, diagnose, infer_domain
from classicalpy.detect import build_signals, build_stack, collect_manifests, infer_architecture
from classicalpy.ingest import Scanner, resolve_source
from classicalpy.models import ProjectReport


def run(source: str, max_files: int = 20_000) -> ProjectReport:
    """Analiza una ruta local o URL de repositorio y devuelve el informe completo.

    Si `source` es una URL, el clon temporal se elimina antes de retornar: el
    informe ya no depende del disco.
    """
    with resolve_source(source) as resolved:
        return analyze_directory(
            resolved.path,
            project_name=resolved.name,
            source=resolved.display,
            source_kind=resolved.kind,
            max_files=max_files,
        )


def analyze_directory(
    root: Path,
    *,
    project_name: str | None = None,
    source: str | None = None,
    source_kind: str = "local",
    max_files: int = 20_000,
) -> ProjectReport:
    """Analiza un directorio ya disponible en disco."""
    root = Path(root).resolve()
    name = project_name or root.name

    # 1. Ingesta: inventario de ficheros del proyecto.
    scanner = Scanner(root, max_files=max_files)
    files, stats = scanner.scan()

    # 2. Deteccion: manifiestos, senales, stack y arquitectura.
    manifests = collect_manifests(root, [f.path for f in files])
    sig = build_signals(files, manifests, stats)
    if sig.declared_name:
        name = sig.declared_name
    stack = build_stack(sig)
    architecture = infer_architecture(sig)

    # 3. Analisis: las cinco secciones del informe.
    domain = infer_domain(sig, root, name)
    modules = build_modules(sig)
    flow = build_flow(sig, architecture.pattern)
    findings = diagnose(sig, modules)
    pitch = build_pitch(sig, domain, architecture.pattern, name)

    report = ProjectReport(
        project_name=name,
        source=source or str(root),
        source_kind=source_kind,
        pitch=pitch,
        domain=domain,
        architecture=architecture,
        stack=stack,
        flow=flow,
        modules=modules,
        findings=findings,
        stats=stats,
        warnings=list(scanner.warnings),
    )

    if stats.total_files == 0:
        report.warnings.append(
            "No se encontro ningun fichero analizable. Comprueba que la ruta es correcta "
            "y que el proyecto no consiste solo en dependencias instaladas."
        )
    return report
