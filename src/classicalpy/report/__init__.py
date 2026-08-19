"""Capa de presentacion: serializa el informe al formato pedido."""

from __future__ import annotations

import json

from classicalpy.models import ProjectReport
from classicalpy.report import markdown

FORMATS = ("markdown", "json", "texto")


def render(report: ProjectReport, fmt: str = "markdown") -> str:
    """Renderiza el informe en el formato indicado."""
    if fmt == "markdown":
        return markdown.render(report)
    if fmt == "json":
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    if fmt == "texto":
        return _plain(markdown.render(report))
    raise ValueError(f"Formato desconocido: {fmt!r}. Opciones: {', '.join(FORMATS)}")


def _plain(md: str) -> str:
    """Markdown despojado de sintaxis, para leer en terminal."""
    out = []
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("<") or stripped in {"---", "```"}:
            continue
        line = line.replace("**", "").replace("`", "").replace("*", "")
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            out += ["", title.upper(), "=" * len(title)]
        else:
            out.append(line.rstrip())
    return "\n".join(out).strip() + "\n"


__all__ = ["render", "markdown", "FORMATS"]
