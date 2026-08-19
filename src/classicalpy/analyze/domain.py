"""Deduccion del proposito, el dominio y el usuario final.

Sin leer el codigo linea a linea, el vocabulario del proyecto es muy revelador:
una carpeta 'checkout' y un modelo 'Order' dicen mas del negocio que cualquier
comentario. Aqui cruzamos ese vocabulario con el README y los manifiestos.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from classicalpy.detect.stack import Signals
from classicalpy.models import Confidence, DomainGuess

# Palabra en rutas/nombres -> (dominio de negocio, usuario final tipico).
DOMAIN_VOCABULARY: dict[str, tuple[str, str]] = {
    "checkout": ("comercio electronico", "personas que compran productos en linea"),
    "cart": ("comercio electronico", "personas que compran productos en linea"),
    "product": ("catalogo de productos", "personas que exploran y compran productos"),
    "order": ("gestion de pedidos", "clientes que compran y el equipo que gestiona los pedidos"),
    "payment": ("cobros y pagos", "clientes que pagan y el equipo financiero"),
    "invoice": ("facturacion", "el equipo administrativo y los clientes facturados"),
    "subscription": ("suscripciones recurrentes", "clientes suscritos al servicio"),
    "inventory": ("gestion de inventario", "el equipo de operaciones y almacen"),
    "shipping": ("logistica y envios", "clientes que reciben pedidos y el equipo de logistica"),
    "booking": ("reservas", "personas que reservan y el negocio que gestiona la disponibilidad"),
    "reservation": ("reservas", "personas que reservan y el negocio que gestiona la disponibilidad"),
    "appointment": ("agenda de citas", "personas que piden cita y el profesional que las atiende"),
    "patient": ("salud", "pacientes y personal sanitario"),
    "doctor": ("salud", "pacientes y personal sanitario"),
    "course": ("formacion en linea", "estudiantes e instructores"),
    "lesson": ("formacion en linea", "estudiantes e instructores"),
    "student": ("educacion", "estudiantes y profesorado"),
    "quiz": ("evaluacion y aprendizaje", "estudiantes y profesorado"),
    "post": ("publicacion de contenido", "lectores y personas que redactan"),
    "blog": ("publicacion de contenido", "lectores y personas que redactan"),
    "article": ("publicacion de contenido", "lectores y equipo editorial"),
    "comment": ("interaccion social sobre contenido", "la comunidad de usuarios"),
    "chat": ("mensajeria", "personas que conversan en tiempo real"),
    "message": ("mensajeria", "personas que conversan"),
    "notification": ("avisos y notificaciones", "usuarios que deben enterarse de cambios"),
    "feed": ("red social / contenido personalizado", "usuarios que consumen contenido de otros"),
    "follow": ("red social", "la comunidad de usuarios"),
    "ticket": ("soporte / incidencias", "clientes que reportan y agentes que resuelven"),
    "issue": ("seguimiento de incidencias", "el equipo que reporta y resuelve"),
    "task": ("gestion de tareas", "equipos que organizan su trabajo"),
    "project": ("gestion de proyectos", "equipos que planifican y ejecutan"),
    "kanban": ("gestion visual de trabajo", "equipos que coordinan tareas"),
    "dashboard": ("analitica y control", "responsables que toman decisiones con datos"),
    "analytics": ("analitica de datos", "responsables de negocio y producto"),
    "report": ("informes", "responsables que necesitan datos agregados"),
    "metric": ("metricas", "responsables tecnicos o de negocio"),
    "admin": ("administracion interna", "el equipo interno que gestiona el sistema"),
    "crm": ("gestion de clientes", "el equipo comercial"),
    "lead": ("captacion comercial", "el equipo comercial"),
    "portfolio": ("presentacion personal o corporativa", "visitantes que evaluan a quien publica"),
    "landing": ("captacion de visitantes", "visitantes que llegan desde marketing"),
    "auth": ("identidad y acceso", "cualquier persona con cuenta en el sistema"),
    "user": ("gestion de usuarios", "las personas registradas en el sistema"),
    "profile": ("perfiles de usuario", "las personas registradas en el sistema"),
    "wallet": ("finanzas personales", "usuarios que gestionan su dinero"),
    "transaction": ("movimientos financieros", "usuarios y el equipo financiero"),
    "budget": ("presupuestos", "personas o equipos que controlan gasto"),
    "recipe": ("recetas y cocina", "personas que cocinan"),
    "workout": ("entrenamiento y salud", "personas que entrenan"),
    "music": ("musica", "oyentes"),
    "video": ("contenido audiovisual", "espectadores"),
    "game": ("videojuego o gamificacion", "jugadores"),
    "map": ("geolocalizacion", "usuarios que buscan o navegan por ubicacion"),
    "weather": ("meteorologia", "personas que consultan el tiempo"),
    "search": ("busqueda y descubrimiento", "usuarios que buscan informacion"),
    "upload": ("gestion de ficheros", "usuarios que suben y comparten archivos"),
    "scrape": ("extraccion de datos", "quien necesita datos de fuentes externas"),
    "crawler": ("rastreo de sitios", "quien necesita datos de fuentes externas"),
    "bot": ("automatizacion conversacional", "usuarios que interactuan con el bot"),
    "webhook": ("integracion entre sistemas", "los sistemas externos que se conectan"),
}

_STOP_WORDS = frozenset(
    {
        "src", "app", "lib", "test", "tests", "index", "main", "utils", "types",
        "config", "components", "pages", "api", "public", "static", "styles",
        "node", "modules", "dist", "build", "the", "and", "for", "with", "this",
    }
)

_WORD_RE = re.compile(r"[a-z][a-z0-9]{2,}")
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_BADGE_RE = re.compile(r"[!\[]\[[^\]]*\]\([^)]*\)")


def infer_domain(sig: Signals, root: Path, project_name: str) -> DomainGuess:
    """Deduce que hace la aplicacion, que problema resuelve y para quien."""
    evidence: list[str] = []

    readme_summary = _read_readme(sig, root)
    if readme_summary:
        evidence.append(f"README: \"{_truncate(readme_summary, 140)}\"")
    if sig.description:
        evidence.append(f"Descripcion declarada en el manifiesto: \"{_truncate(sig.description, 140)}\"")

    hits = _vocabulary_hits(sig)
    domains = [DOMAIN_VOCABULARY[word][0] for word, _ in hits]
    users = [DOMAIN_VOCABULARY[word][1] for word, _ in hits]

    if hits:
        evidence.append(
            "Vocabulario recurrente en rutas y ficheros: "
            + ", ".join(f"'{w}' ({c}x)" for w, c in hits[:6])
        )

    # El proposito: lo declarado gana sobre lo deducido.
    declared = sig.description or readme_summary
    if declared:
        purpose = _truncate(_clean(declared), 220)
        confidence = Confidence.ALTA
    elif domains:
        purpose = (
            f"Aplicacion de {domains[0]}"
            + (f", con componentes de {domains[1]}" if len(domains) > 1 else "")
            + "."
        )
        confidence = Confidence.MEDIA
    else:
        purpose = (
            f"No hay descripcion declarada ni vocabulario de negocio reconocible. "
            f"Por su estructura, '{project_name}' es codigo de aplicacion de proposito no evidente."
        )
        confidence = Confidence.BAJA

    problem = _infer_problem(sig, domains)
    end_user = _infer_end_user(sig, users)

    if not sig.readme_path:
        evidence.append("No hay README en la raiz: el proposito se deduce de la estructura, no de la documentacion.")

    return DomainGuess(
        purpose=purpose,
        problem=problem,
        end_user=end_user,
        confidence=confidence,
        evidence=evidence,
    )


def _vocabulary_hits(sig: Signals) -> list[tuple[str, int]]:
    """Cuenta que palabras de negocio aparecen en rutas, ordenadas por frecuencia."""
    counter: Counter[str] = Counter()
    for path in sig.file_set:
        for word in _WORD_RE.findall(path):
            if word in DOMAIN_VOCABULARY:
                counter[word] += 1
    # Una sola aparicion suele ser ruido (p.ej. un unico fichero 'user.ts' generico).
    return [(w, c) for w, c in counter.most_common(10) if c >= 1]


def _infer_problem(sig: Signals, domains: list[str]) -> str:
    if domains:
        unique = list(dict.fromkeys(domains))[:3]
        return (
            "Automatiza y centraliza las operaciones de "
            + ", ".join(unique)
            + ", evitando que se gestionen a mano o en herramientas dispersas."
        )
    if sig.backends and not sig.frontends:
        return (
            "Expone capacidades de un sistema a traves de una API para que otras "
            "aplicaciones las consuman sin duplicar la logica."
        )
    if sig.frontends or sig.meta_frameworks:
        return (
            "Da una interfaz web a un conjunto de datos u operaciones que de otro "
            "modo requeririan acceso tecnico directo."
        )
    return "El problema de negocio no es deducible con la informacion disponible en el repositorio."


def _infer_end_user(sig: Signals, users: list[str]) -> str:
    if users:
        unique = list(dict.fromkeys(users))
        primary = unique[0]
        if len(unique) > 1:
            return f"Principalmente {primary}; secundariamente {unique[1]}."
        return primary.capitalize() + "."
    if sig.backends and not sig.frontends and not sig.meta_frameworks:
        return "Otros sistemas y equipos de desarrollo que integran esta API, no personas usuarias finales."
    if sig.has_dir("admin") or sig.has_dir("dashboard"):
        return "El equipo interno que administra el sistema."
    return "No hay senales suficientes para identificar al usuario final."


def build_pitch(sig: Signals, domain: DomainGuess, architecture_pattern: str, name: str) -> str:
    """La explicacion en 5 segundos: dos frases en lenguaje cotidiano."""
    stack_words = (
        sig.meta_frameworks or sig.frontends or sig.backends or sorted(sig.ecosystems) or ["codigo"]
    )
    first = _truncate(_clean(domain.purpose), 200)
    if not first.endswith("."):
        first += "."
    if not first.lower().startswith(("aplicacion", "no hay", "es ")):
        first = f"{name} es un proyecto que se describe asi: {first}"

    second = (
        f"Por dentro esta construido con {', '.join(stack_words[:3])} "
        f"siguiendo un patron de {architecture_pattern.lower()}, "
        f"y suma {_miles(sig.stats.total_lines)} lineas de codigo repartidas en "
        f"{_miles(sig.stats.total_files)} ficheros."
    )

    return f"{first} {second}"


def _miles(value: int) -> str:
    """Formatea con punto como separador de miles (convencion en espanol)."""
    return f"{value:,}".replace(",", ".")


def _read_readme(sig: Signals, root: Path) -> str | None:
    """Extrae el primer parrafo util del README, saltando titulo y badges."""
    if not sig.readme_path:
        return None
    try:
        raw = (root / sig.readme_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    raw = _BADGE_RE.sub("", raw)
    for block in raw.split("\n\n"):
        text = block.strip()
        if not text or text.startswith(("#", ">", "|", "```", "-", "*", "<")):
            continue
        return _clean(text)
    # Sin parrafo: al menos el titulo principal dice algo.
    if match := _HEADING_RE.search(raw):
        return _clean(match.group(1))
    return None


def _clean(text: str) -> str:
    text = re.sub(r"[`*_#]", "", text)
    return " ".join(text.split())


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"
