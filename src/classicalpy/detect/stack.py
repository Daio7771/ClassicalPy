"""Deteccion del stack y del patron arquitectonico.

Primero se condensa todo lo escaneado en un objeto :class:`Signals` (las
"pistas" del proyecto). El resto del analisis --stack, dominio, flujo,
diagnostico-- razona sobre esas pistas y nunca vuelve a tocar el disco.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from classicalpy.detect.knowledge import describe
from classicalpy.models import (
    ArchitectureGuess,
    Confidence,
    FileInfo,
    Manifest,
    ProjectStats,
    TechEntry,
)

# Paquete -> etiqueta de familia. Sirve para responder "que hay aqui" de un vistazo.
FRONTEND_FRAMEWORKS = {
    "react": "React", "vue": "Vue", "svelte": "Svelte", "@angular/core": "Angular",
    "solid-js": "SolidJS", "preact": "Preact", "htmx": "htmx", "alpinejs": "Alpine.js",
}
META_FRAMEWORKS = {
    "next": "Next.js", "nuxt": "Nuxt", "remix": "Remix", "@sveltejs/kit": "SvelteKit",
    "astro": "Astro", "gatsby": "Gatsby",
}
BACKEND_FRAMEWORKS = {
    "express": "Express", "fastify": "Fastify", "koa": "Koa", "@nestjs/core": "NestJS",
    "hono": "Hono", "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
    "litestar": "Litestar", "sanic": "Sanic", "tornado": "Tornado",
    "laravel/framework": "Laravel", "symfony/framework-bundle": "Symfony",
    "rails": "Ruby on Rails", "sinatra": "Sinatra",
    "github.com/gin-gonic/gin": "Gin", "github.com/labstack/echo": "Echo",
    "actix-web": "Actix Web", "axum": "Axum",
}
DATA_LAYER = {
    "prisma": "Prisma", "@prisma/client": "Prisma", "typeorm": "TypeORM",
    "sequelize": "Sequelize", "mongoose": "Mongoose", "drizzle-orm": "Drizzle",
    "sqlalchemy": "SQLAlchemy", "knex": "Knex", "pg": "PostgreSQL", "psycopg": "PostgreSQL",
    "psycopg2-binary": "PostgreSQL", "asyncpg": "PostgreSQL", "mysql2": "MySQL",
    "mongodb": "MongoDB", "pymongo": "MongoDB", "better-sqlite3": "SQLite",
    "@supabase/supabase-js": "Supabase", "firebase": "Firebase",
}
AUTH_LIBS = {
    "next-auth", "passport", "jsonwebtoken", "python-jose", "authlib",
    "@clerk/nextjs", "bcrypt", "bcryptjs", "passlib",
}
TEST_LIBS = {
    "jest", "vitest", "mocha", "pytest", "cypress", "@playwright/test",
    "@testing-library/react", "supertest",
}

# Fichero (nombre exacto o sufijo de ruta) -> (categoria, rol) para infraestructura.
INFRA_FILES: dict[str, tuple[str, str]] = {
    "dockerfile": ("Contenedores", "Empaqueta la aplicacion con sus dependencias para que corra igual en cualquier maquina."),
    "docker-compose.yml": ("Orquestacion local", "Levanta la aplicacion y sus servicios de apoyo (BD, cache) con un solo comando."),
    "docker-compose.yaml": ("Orquestacion local", "Levanta la aplicacion y sus servicios de apoyo (BD, cache) con un solo comando."),
    "vercel.json": ("Despliegue", "Configura el despliegue serverless en Vercel."),
    "netlify.toml": ("Despliegue", "Configura el build y despliegue en Netlify."),
    "fly.toml": ("Despliegue", "Configura el despliegue en Fly.io."),
    "render.yaml": ("Despliegue", "Declara los servicios a desplegar en Render."),
    "procfile": ("Despliegue", "Declara los procesos que arranca la plataforma de hosting."),
    "makefile": ("Automatizacion", "Centraliza los comandos habituales del proyecto."),
    "nginx.conf": ("Infraestructura", "Configura el proxy inverso que expone la aplicacion."),
}


@dataclass(slots=True)
class Signals:
    """Todo lo que sabemos del proyecto, ya condensado."""

    files: list[FileInfo] = field(default_factory=list)
    manifests: list[Manifest] = field(default_factory=list)
    stats: ProjectStats = field(default_factory=ProjectStats)

    all_deps: dict[str, str] = field(default_factory=dict)  # nombre -> version
    dev_deps: dict[str, str] = field(default_factory=dict)
    ecosystems: set[str] = field(default_factory=set)
    scripts: dict[str, str] = field(default_factory=dict)

    dir_set: set[str] = field(default_factory=set)  # todas las carpetas, en minusculas
    top_dirs: list[str] = field(default_factory=list)  # carpetas de primer nivel
    file_set: set[str] = field(default_factory=set)  # rutas relativas en minusculas
    basenames: set[str] = field(default_factory=set)

    frontends: list[str] = field(default_factory=list)
    meta_frameworks: list[str] = field(default_factory=list)
    backends: list[str] = field(default_factory=list)
    datastores: list[str] = field(default_factory=list)

    description: str | None = None
    declared_name: str | None = None
    readme_path: str | None = None

    def has_dep(self, *names: str) -> bool:
        return any(n in self.all_deps or n in self.dev_deps for n in names)

    def has_dir(self, *names: str) -> bool:
        """Carpeta con ese nombre a cualquier profundidad."""
        return any(n in self.dir_set for n in names)

    def has_top_dir(self, *names: str) -> bool:
        """Carpeta en el primer nivel del repositorio.

        Para las reglas que hablan de la *topologia* del proyecto (monorepo,
        cliente/servidor) esto es lo correcto: un 'apps/' dentro de un fixture
        de tests no convierte el repositorio en un monorepo.
        """
        return any(n in self.top_dirs for n in names)

    def has_file(self, *names: str) -> bool:
        return any(n in self.basenames for n in names)

    def path_contains(self, fragment: str) -> bool:
        return any(fragment in p for p in self.file_set)


def build_signals(
    files: list[FileInfo], manifests: list[Manifest], stats: ProjectStats
) -> Signals:
    """Condensa el escaneo en el objeto de pistas que consume todo el analisis."""
    sig = Signals(files=files, manifests=manifests, stats=stats)

    for manifest in manifests:
        sig.ecosystems.add(manifest.ecosystem)
        sig.all_deps.update(manifest.dependencies)
        sig.dev_deps.update(manifest.dev_dependencies)
        sig.scripts.update(manifest.scripts)
        if manifest.description and not sig.description:
            sig.description = manifest.description
        if manifest.project_name and not sig.declared_name:
            sig.declared_name = manifest.project_name

    for info in files:
        lower = info.path.lower()
        sig.file_set.add(lower)
        sig.basenames.add(info.name.lower())
        parts = lower.split("/")[:-1]
        for depth in range(len(parts)):
            sig.dir_set.add(parts[depth])
        if parts:
            sig.top_dirs.append(parts[0])
        if info.name.lower().startswith("readme") and "/" not in info.path:
            sig.readme_path = info.path

    sig.top_dirs = sorted(set(sig.top_dirs))

    known = {**sig.all_deps, **sig.dev_deps}
    sig.frontends = sorted({v for k, v in FRONTEND_FRAMEWORKS.items() if k in known})
    sig.meta_frameworks = sorted({v for k, v in META_FRAMEWORKS.items() if k in known})
    sig.backends = sorted({v for k, v in BACKEND_FRAMEWORKS.items() if k in known})
    sig.datastores = sorted({v for k, v in DATA_LAYER.items() if k in known})
    return sig


def build_stack(sig: Signals) -> list[TechEntry]:
    """Construye la tabla Tecnologia | Rol en este Proyecto.

    Mezcla tres fuentes: lenguajes detectados por volumen de codigo,
    dependencias declaradas y ficheros de infraestructura.
    """
    entries: list[TechEntry] = []
    seen: set[str] = set()

    def add(entry: TechEntry) -> None:
        key = entry.name.lower()
        if key not in seen:
            seen.add(key)
            entries.append(entry)

    # 1. Lenguajes, ordenados por cuanto codigo hay escrito en ellos.
    total = max(sig.stats.total_lines, 1)
    for language, lines in sorted(
        sig.stats.lines_by_language.items(), key=lambda kv: kv[1], reverse=True
    ):
        if language in {"JSON", "YAML", "TOML", "Config", "Texto", "XML"} or lines == 0:
            continue
        share = 100 * lines / total
        if share < 1.0:
            continue
        add(
            TechEntry(
                name=language,
                category="Lenguaje",
                role=f"{_language_role(language)} Concentra el {share:.0f}% del codigo del proyecto.",
                evidence=f"{lines:,} lineas en {sig.stats.files_by_language.get(language, 0)} ficheros",
            )
        )

    # 2. Dependencias declaradas. Las de produccion primero: definen la arquitectura.
    for deps, kind in ((sig.all_deps, "produccion"), (sig.dev_deps, "desarrollo")):
        for name, version in sorted(deps.items()):
            if (described := describe(name)) is None:
                continue
            category, role = described
            add(
                TechEntry(
                    name=name,
                    category=category if kind == "produccion" else f"{category} (dev)",
                    role=role,
                    version=_clean_version(version),
                    ecosystem=_ecosystem_of(name, sig),
                    evidence=f"declarado en {_manifest_of(name, sig)}",
                )
            )

    # 3. Infraestructura: no esta en ningun manifiesto pero define como se despliega.
    for basename, (category, role) in INFRA_FILES.items():
        if basename in sig.basenames or any(b.startswith(basename) for b in sig.basenames):
            add(TechEntry(name=_pretty_infra(basename), category=category, role=role,
                          evidence=basename))
    if sig.path_contains(".github/workflows/"):
        add(
            TechEntry(
                name="GitHub Actions",
                category="CI/CD",
                role="Ejecuta pruebas y despliegues automaticamente en cada cambio del repositorio.",
                evidence=".github/workflows/",
            )
        )
    if sig.has_dir("terraform") or sig.has_file("main.tf"):
        add(
            TechEntry(
                name="Terraform",
                category="Infraestructura como codigo",
                role="Declara la infraestructura en ficheros versionados en vez de configurarla a mano.",
                evidence="ficheros .tf",
            )
        )
    return entries


_LANGUAGE_ROLES: dict[str, str] = {
    "Python": "Lenguaje del backend y de la logica de negocio.",
    "TypeScript": "Lenguaje principal con tipado estatico: los contratos entre modulos se verifican en compilacion.",
    "JavaScript": "Lenguaje de la logica de aplicacion, en cliente y/o servidor.",
    "HTML": "Estructura del marcado que se entrega al navegador.",
    "CSS": "Capa de presentacion visual.",
    "Vue": "Componentes de interfaz de un solo fichero (plantilla, logica y estilo juntos).",
    "Svelte": "Componentes de interfaz compilados a JavaScript sin runtime.",
    "Astro": "Paginas y componentes del sitio, renderizados en build.",
    "SQL": "Consultas, esquemas o migraciones de la base de datos.",
    "PHP": "Lenguaje del backend.",
    "Go": "Lenguaje de los servicios de backend.",
    "Rust": "Lenguaje de los componentes de rendimiento critico.",
    "Java": "Lenguaje del backend.",
    "C#": "Lenguaje del backend.",
    "Ruby": "Lenguaje del backend.",
    "Shell": "Scripts de automatizacion y despliegue.",
    "PowerShell": "Scripts de automatizacion en Windows.",
    "Markdown": "Documentacion del proyecto.",
    "GraphQL": "Definicion del esquema de la API.",
}


def _language_role(language: str) -> str:
    return _LANGUAGE_ROLES.get(language, f"Codigo escrito en {language}.")


def _clean_version(raw: str) -> str | None:
    version = raw.strip().lstrip("^~>=< ")
    return version or None


def _ecosystem_of(name: str, sig: Signals) -> str | None:
    for manifest in sig.manifests:
        if name in manifest.dependencies or name in manifest.dev_dependencies:
            return manifest.ecosystem
    return None


def _manifest_of(name: str, sig: Signals) -> str:
    for manifest in sig.manifests:
        if name in manifest.dependencies or name in manifest.dev_dependencies:
            return manifest.path
    return "manifiesto"


def _pretty_infra(basename: str) -> str:
    return {
        "dockerfile": "Docker",
        "docker-compose.yml": "Docker Compose",
        "docker-compose.yaml": "Docker Compose",
        "procfile": "Procfile",
        "makefile": "Make",
        "nginx.conf": "Nginx",
    }.get(basename, basename)


# ------------------------------------------------------------------ arquitectura

# Nombres de carpeta que delatan una separacion cliente/servidor explicita.
_CLIENT_DIRS = ("client", "frontend", "front", "web", "ui")
_SERVER_DIRS = ("server", "backend", "back", "api")


def infer_architecture(sig: Signals) -> ArchitectureGuess:
    """Deduce el patron arquitectonico a partir de las pistas acumuladas.

    Las reglas se evaluan de la mas especifica a la mas generica y la primera
    que encaja gana, para no diluir el diagnostico en etiquetas ambiguas.
    """
    rationale: list[str] = []

    manifest_count = sum(1 for m in sig.manifests if m.ecosystem == "node")
    is_monorepo = (
        manifest_count > 1
        or sig.has_top_dir("packages", "apps")
        or sig.has_file("pnpm-workspace.yaml", "lerna.json", "turbo.json")
    )

    has_client_dir = sig.has_top_dir(*_CLIENT_DIRS)
    has_server_dir = sig.has_top_dir(*_SERVER_DIRS)

    # 1. Microservicios: varios servicios contenedorizados de forma independiente.
    dockerfiles = sum(1 for p in sig.file_set if p.rsplit("/", 1)[-1].startswith("dockerfile"))
    if dockerfiles >= 3 and (sig.has_top_dir("services") or is_monorepo):
        rationale.append(f"{dockerfiles} Dockerfiles independientes: cada servicio se empaqueta por separado.")
        if sig.has_top_dir("services"):
            rationale.append("Existe una carpeta 'services/' que agrupa unidades desplegables.")
        return ArchitectureGuess("Microservicios / servicios contenedorizados", rationale, Confidence.MEDIA)

    # 2. Monorepo: varios paquetes con ciclo de vida propio bajo un mismo repositorio.
    if is_monorepo and sig.has_top_dir("packages", "apps"):
        rationale.append("Carpetas 'packages/' o 'apps/' con manifiestos propios: multiples paquetes en un repositorio.")
        if sig.has_dep("turbo", "nx", "lerna"):
            rationale.append("Herramienta de monorepo declarada para orquestar builds compartidos.")
        return ArchitectureGuess("Monorepo multi-paquete", rationale, Confidence.ALTA)

    # 3. Meta-framework: SSR + enrutado por ficheros, front y back en el mismo proceso.
    if sig.meta_frameworks:
        name = sig.meta_frameworks[0]
        rationale.append(f"{name} gobierna renderizado y enrutado: la frontera front/back vive dentro del propio framework.")
        if sig.path_contains("/api/") or sig.has_dir("api"):
            rationale.append("Hay rutas de API dentro del mismo proyecto: el backend no es un despliegue aparte.")
        if sig.has_dir("app"):
            rationale.append("Enrutado por sistema de ficheros ('app/'): la estructura de carpetas ES el mapa de URLs.")
        elif sig.has_dir("pages"):
            rationale.append("Enrutado por sistema de ficheros ('pages/'): cada fichero es una ruta publica.")
        return ArchitectureGuess(
            f"Fullstack con renderizado en servidor ({name})", rationale, Confidence.ALTA
        )

    # 4. Cliente-servidor desacoplado: SPA que consume una API separada.
    if has_client_dir and has_server_dir:
        rationale.append("Carpetas de cliente y de servidor separadas: dos despliegues independientes que hablan por HTTP.")
        if sig.frontends:
            rationale.append(f"El cliente es una SPA construida con {', '.join(sig.frontends)}.")
        if sig.backends:
            rationale.append(f"El servidor expone una API con {', '.join(sig.backends)}.")
        return ArchitectureGuess("Cliente-servidor desacoplado (SPA + API)", rationale, Confidence.ALTA)

    # 5. MVC clasico: framework con convenciones de carpeta impuestas.
    mvc_dirs = [d for d in ("models", "views", "controllers", "templates") if sig.has_dir(d)]
    if len(mvc_dirs) >= 2 or sig.has_dep("django", "rails", "laravel/framework"):
        rationale.append(f"Carpetas de convencion MVC presentes: {', '.join(mvc_dirs) or 'impuestas por el framework'}.")
        if sig.backends:
            rationale.append(f"El framework {sig.backends[0]} impone la separacion modelo / vista / controlador.")
        return ArchitectureGuess("MVC (modelo-vista-controlador)", rationale, Confidence.ALTA)

    # 6. Arquitectura por capas / hexagonal.
    layered = [d for d in ("domain", "application", "infrastructure", "adapters", "ports", "usecases", "entities") if sig.has_dir(d)]
    if len(layered) >= 2:
        rationale.append(f"Capas explicitas: {', '.join(layered)}. La logica de negocio esta aislada de la infraestructura.")
        return ArchitectureGuess("Arquitectura por capas / hexagonal", rationale, Confidence.MEDIA)

    # 7. Solo API, sin capa de vista propia.
    if sig.backends and not sig.frontends and not sig.has_dir("templates", "views", "public", "static"):
        rationale.append(f"Hay servidor ({', '.join(sig.backends)}) pero ninguna capa de vista: el proyecto es un servicio consumido por terceros.")
        return ArchitectureGuess("Servicio de API (backend sin interfaz)", rationale, Confidence.ALTA)

    # 8. Monolito: un mismo servidor atiende la API y sirve su propia interfaz.
    if sig.backends and sig.has_dir("templates", "views", "public", "static"):
        vista = [d for d in ("templates", "views", "public", "static") if sig.has_dir(d)]
        rationale.append(
            f"El servidor ({', '.join(sig.backends)}) sirve tambien su propia interfaz desde "
            f"'{vista[0]}/': no hay un despliegue de frontend separado."
        )
        if sig.frontends:
            rationale.append(f"La interfaz usa {', '.join(sig.frontends)} embebido, no como aplicacion independiente.")
        else:
            rationale.append("La interfaz es HTML/CSS/JS servido directamente, sin paso de build.")
        return ArchitectureGuess(
            "Monolito web (servidor + interfaz en un mismo despliegue)", rationale, Confidence.ALTA
        )

    # 9. SPA pura contra un backend gestionado o externo.
    if sig.frontends and not sig.backends:
        rationale.append(f"Interfaz con {', '.join(sig.frontends)} sin servidor propio en el repositorio.")
        if sig.has_dep("@supabase/supabase-js", "firebase"):
            rationale.append("La persistencia y la autenticacion se delegan a un backend gestionado (BaaS).")
            return ArchitectureGuess("SPA sobre backend gestionado (BaaS)", rationale, Confidence.ALTA)
        rationale.append("Los datos deben venir de una API externa no incluida en este repositorio.")
        return ArchitectureGuess("SPA (aplicacion de pagina unica)", rationale, Confidence.MEDIA)

    # 10. Jamstack / sitio estatico.
    if sig.stats.files_by_language.get("HTML", 0) > 0 and not sig.backends and not sig.frontends:
        rationale.append("HTML y assets sin servidor de aplicacion: el sitio se sirve como ficheros estaticos.")
        return ArchitectureGuess("Sitio estatico / Jamstack", rationale, Confidence.MEDIA)

    # 11. Sin senales suficientes.
    rationale.append("No hay suficientes senales estructurales para clasificar el patron con confianza.")
    if sig.top_dirs:
        rationale.append(f"Carpetas de primer nivel observadas: {', '.join(sig.top_dirs[:8])}.")
    return ArchitectureGuess("Estructura modular sin patron canonico identificado", rationale, Confidence.BAJA)
