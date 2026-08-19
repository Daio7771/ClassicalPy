"""Renderizado del informe a Markdown.

La estructura de salida es fija y deliberada: cada seccion responde a una
pregunta distinta, y estan ordenadas de menos a mas detalle tecnico para que
un perfil no tecnico pueda parar de leer cuando quiera.
"""

from __future__ import annotations

from classicalpy.models import FindingKind, ProjectReport

_KIND_LABEL = {
    FindingKind.FORTALEZA: "Bien resuelto",
    FindingKind.RIESGO: "Riesgo",
    FindingKind.MEJORA: "Area de mejora",
}
_KIND_ICON = {
    FindingKind.FORTALEZA: "✅",
    FindingKind.RIESGO: "🚨",
    FindingKind.MEJORA: "⚠️",
}


def render(report: ProjectReport) -> str:
    """Devuelve el informe completo en Markdown."""
    parts = [
        _header(report),
        _section_pitch(report),
        _section_stack(report),
        _section_flow(report),
        _section_modules(report),
        _section_diagnosis(report),
        _footer(report),
    ]
    return "\n\n".join(p for p in parts if p).strip() + "\n"


def _header(report: ProjectReport) -> str:
    origen = "repositorio remoto" if report.source_kind == "git" else "carpeta local"
    return (
        f"# Informe de arquitectura — {report.project_name}\n\n"
        f"> Fuente: `{report.source}` ({origen})  \n"
        f"> Generado: {report.generated_at}  \n"
        f"> Analisis estatico, sin ejecucion del codigo."
    )


def _section_pitch(report: ProjectReport) -> str:
    lines = ["## 🎯 Explicacion en 5 segundos", "", report.pitch]

    if report.domain:
        lines += [
            "",
            f"**Que problema resuelve.** {report.domain.problem}",
            "",
            f"**Quien es el usuario final.** {report.domain.end_user}",
            "",
            f"*Confianza de esta deduccion: {report.domain.confidence.value}.*",
        ]
        if report.domain.evidence:
            lines += ["", "<details><summary>En que se basa</summary>", ""]
            lines += [f"- {item}" for item in report.domain.evidence]
            lines += ["", "</details>"]
    return "\n".join(lines)


def _section_stack(report: ProjectReport) -> str:
    lines = ["## 🏗️ Ficha Tecnica y Arquitectura", ""]

    if report.architecture:
        lines += [
            f"**Patron arquitectonico:** {report.architecture.pattern} "
            f"*(confianza {report.architecture.confidence.value})*",
            "",
        ]
        lines += [f"- {reason}" for reason in report.architecture.rationale]
        lines.append("")

    if not report.stack:
        lines.append("_No se detectaron tecnologias identificables._")
        return "\n".join(lines)

    lines += [
        "| Tecnologia | Categoria | Version | Rol en este Proyecto |",
        "| --- | --- | --- | --- |",
    ]
    for tech in report.stack:
        version = f"`{tech.version}`" if tech.version else "—"
        lines.append(
            f"| **{_escape(tech.name)}** | {_escape(tech.category)} "
            f"| {version} | {_escape(tech.role)} |"
        )

    stats = report.stats
    lines += [
        "",
        f"**Volumen:** {_miles(stats.total_files)} ficheros · {_miles(stats.total_lines)} lineas · "
        f"{stats.total_bytes / 1_048_576:.1f} MB de codigo analizado.",
    ]
    return "\n".join(lines)


def _section_flow(report: ProjectReport) -> str:
    lines = ["## 🔄 Flujo de Trabajo Principal", ""]
    if not report.flow:
        lines.append("_No se pudo reconstruir el flujo con la informacion disponible._")
        return "\n".join(lines)

    lines.append("Recorrido de una peticion, de la interfaz al dato y de vuelta:")
    lines.append("")
    for step in report.flow:
        evidence = f"  \n  <sub>Evidencia: `{step.evidence}`</sub>" if step.evidence else ""
        lines.append(f"{step.order}. **[{step.actor}] {step.title}** — {step.detail}{evidence}")
    return "\n".join(lines)


def _section_modules(report: ProjectReport) -> str:
    lines = ["## 📂 Mapa Conceptual de Modulos", ""]
    if not report.modules:
        lines.append("_No se identificaron modulos relevantes._")
        return "\n".join(lines)

    lines.append("Que responsabilidad tiene cada carpeta clave (no que ficheros contiene):")
    lines.append("")
    for module in report.modules:
        indent = "  " * module.path.count("/")
        langs = f" · {', '.join(module.languages[:2])}" if module.languages else ""
        lines.append(
            f"{indent}- **`{module.path}`** — *{module.role}* "
            f"({module.file_count} ficheros{langs})  \n"
            f"{indent}  {module.purpose}"
        )
        if module.key_files:
            # Relativos al modulo: tres '__init__.py' de subcarpetas distintas
            # serian indistinguibles si mostraramos solo el nombre.
            prefix = "" if module.path == "." else module.path + "/"
            keys = ", ".join(f"`{k.removeprefix(prefix)}`" for k in module.key_files[:3])
            lines.append(f"{indent}  <sub>Ficheros de referencia: {keys}</sub>")
    return "\n".join(lines)


def _section_diagnosis(report: ProjectReport) -> str:
    lines = ["## 💡 Diagnostico del Codigo", ""]
    if not report.findings:
        lines.append("_Sin hallazgos destacables._")
        return "\n".join(lines)

    for kind in (FindingKind.FORTALEZA, FindingKind.RIESGO, FindingKind.MEJORA):
        group = report.findings_of(kind)
        if not group:
            continue
        lines += [f"### {_KIND_ICON[kind]} {_KIND_LABEL[kind]}", ""]
        for finding in group:
            lines.append(f"**{finding.title}**  ")
            lines.append(f"{finding.detail}  ")
            if finding.impact:
                lines.append(f"*Impacto:* {finding.impact}  ")
            if finding.evidence:
                lines.append(f"<sub>Evidencia: `{finding.evidence}`</sub>")
            lines.append("")
    return "\n".join(lines).rstrip()


def _footer(report: ProjectReport) -> str:
    if not report.warnings:
        return ""
    lines = ["---", "", "### ⚙️ Avisos del analisis", ""]
    lines += [f"- {w}" for w in report.warnings]
    return "\n".join(lines)


def _escape(text: str) -> str:
    """Evita que un pipe en el texto rompa la tabla Markdown."""
    return text.replace("|", "\\|").replace("\n", " ")


def _miles(value: int) -> str:
    return f"{value:,}".replace(",", ".")
