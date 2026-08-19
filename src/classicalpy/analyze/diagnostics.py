"""Diagnostico: que esta bien resuelto y donde hay deuda tecnica visible.

Cada regla es una funcion que mira las senales y devuelve cero o mas hallazgos.
Ninguna regla inventa: si no hay evidencia observable, no se emite el hallazgo.
Se declara explicitamente el impacto para que un perfil no tecnico entienda
por que importa.
"""

from __future__ import annotations

from collections.abc import Callable

from classicalpy.detect.stack import AUTH_LIBS, TEST_LIBS, Signals
from classicalpy.models import Finding, FindingKind, ModuleNode

# Umbrales del analisis. Explicitos y en un solo sitio para poder discutirlos.
FICHERO_GRANDE = 400  # lineas a partir de las cuales un fichero es dificil de mantener
FICHERO_ENORME = 800
RATIO_TEST_BAJO = 0.05  # menos de un 5% de ficheros de test
RATIO_TEST_BUENO = 0.15
CARPETA_SATURADA = 40  # ficheros directos en una sola carpeta

Rule = Callable[[Signals, list[ModuleNode]], list[Finding]]


def _f(kind: FindingKind, title: str, detail: str, evidence: str | None, impact: str) -> Finding:
    return Finding(kind=kind, title=title, detail=detail, evidence=evidence, impact=impact)


# ------------------------------------------------------------------- fortalezas


def _rule_tests(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    ratio = sig.stats.test_ratio
    frameworks = sorted({d for d in (*sig.all_deps, *sig.dev_deps) if d in TEST_LIBS})

    if sig.stats.test_files == 0:
        return [
            _f(
                FindingKind.RIESGO,
                "No hay pruebas automatizadas",
                "No se ha encontrado ningun fichero de test en el repositorio. Cada cambio se valida "
                "a mano, lo que hace que refactorizar sea caro y arriesgado.",
                "0 ficheros de test detectados",
                "Alto: las regresiones se descubren en produccion, no en desarrollo.",
            )
        ]
    if ratio < RATIO_TEST_BAJO:
        return [
            _f(
                FindingKind.MEJORA,
                "Cobertura de pruebas escasa",
                f"Solo {sig.stats.test_files} de los ficheros de codigo son tests ({ratio:.0%}). "
                "Existe la infraestructura de pruebas pero cubre una fraccion pequena del sistema.",
                f"{sig.stats.test_files} ficheros de test",
                "Medio: partes del sistema cambian sin red de seguridad.",
            )
        ]
    if ratio >= RATIO_TEST_BUENO:
        return [
            _f(
                FindingKind.FORTALEZA,
                "Suite de pruebas consolidada",
                f"{sig.stats.test_files} ficheros de test ({ratio:.0%} del codigo)"
                + (f", ejecutados con {', '.join(frameworks)}" if frameworks else "")
                + ". El equipo puede cambiar el codigo con la confianza de que una rotura se detecta sola.",
                f"{sig.stats.test_files} ficheros de test",
                "Reduce el coste de mantener y evolucionar el proyecto.",
            )
        ]
    return []


def _rule_typing(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    ts_lines = sig.stats.lines_by_language.get("TypeScript", 0)
    js_lines = sig.stats.lines_by_language.get("JavaScript", 0)
    findings: list[Finding] = []

    if ts_lines > 0 and js_lines > ts_lines * 0.3:
        findings.append(
            _f(
                FindingKind.MEJORA,
                "Migracion a TypeScript incompleta",
                f"Conviven {ts_lines:,} lineas de TypeScript con {js_lines:,} de JavaScript sin tipar. "
                "Las garantias del tipado se pierden en cada frontera entre ambos mundos.".replace(",", "."),
                f"TypeScript {ts_lines} / JavaScript {js_lines} lineas",
                "Medio: los errores de contrato solo aparecen en tiempo de ejecucion.",
            )
        )
    elif ts_lines > 0 and js_lines == 0:
        findings.append(
            _f(
                FindingKind.FORTALEZA,
                "Base de codigo enteramente tipada",
                "Todo el codigo de aplicacion esta en TypeScript. Los contratos entre modulos se "
                "verifican antes de ejecutar, no en produccion.",
                f"{ts_lines} lineas de TypeScript, 0 de JavaScript",
                "Menos errores de integracion y refactorizaciones mas seguras.",
            )
        )

    if sig.has_dep("mypy") or sig.has_dep("pydantic"):
        findings.append(
            _f(
                FindingKind.FORTALEZA,
                "Tipado verificado en Python",
                "El proyecto declara herramientas de verificacion de tipos o validacion por anotaciones, "
                "lo que convierte las anotaciones en garantias reales y no en documentacion.",
                "mypy" if sig.has_dep("mypy") else "pydantic",
                "Detecta desajustes de datos antes de que lleguen al usuario.",
            )
        )
    return findings


def _rule_quality_tooling(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    tools = [t for t in ("eslint", "prettier", "ruff", "black", "husky") if sig.has_dep(t)]
    if len(tools) >= 2:
        return [
            _f(
                FindingKind.FORTALEZA,
                "Calidad de codigo automatizada",
                f"El proyecto usa {', '.join(tools)}: el estilo y los errores comunes se detectan "
                "de forma automatica, no en la revision manual de cada cambio.",
                ", ".join(tools),
                "Revisiones de codigo centradas en el diseno, no en el formato.",
            )
        ]
    if not tools:
        return [
            _f(
                FindingKind.MEJORA,
                "Sin linter ni formateador declarado",
                "No hay herramienta de analisis estatico configurada. El estilo depende de la disciplina "
                "de cada persona y los errores triviales llegan a la revision.",
                "no se encontro eslint / ruff / prettier / black",
                "Bajo, pero acumula friccion en cada revision de codigo.",
            )
        ]
    return []


def _rule_ci(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    if sig.path_contains(".github/workflows/") or sig.has_file(".gitlab-ci.yml", "jenkinsfile"):
        return [
            _f(
                FindingKind.FORTALEZA,
                "Integracion continua configurada",
                "Existen flujos automaticos que se ejecutan en cada cambio del repositorio, "
                "de modo que nada se integra sin pasar antes las comprobaciones.",
                ".github/workflows/" if sig.path_contains(".github/workflows/") else "configuracion de CI",
                "Evita que codigo roto llegue a la rama principal.",
            )
        ]
    return [
        _f(
            FindingKind.MEJORA,
            "Sin integracion continua",
            "No hay ningun flujo automatico que valide los cambios. Las comprobaciones dependen de "
            "que cada persona se acuerde de ejecutarlas en su maquina.",
            "no se encontro .github/workflows ni equivalente",
            "Medio: aumenta la probabilidad de romper la rama principal.",
        )
    ]


def _rule_containerization(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    if any(b.startswith("dockerfile") for b in sig.basenames):
        return [
            _f(
                FindingKind.FORTALEZA,
                "Entorno reproducible con contenedores",
                "La aplicacion se empaqueta con sus dependencias, asi que se comporta igual en el "
                "portatil de cualquier persona y en produccion.",
                "Dockerfile",
                "Elimina la clase de fallos de 'en mi maquina funciona'.",
            )
        ]
    return []


# ------------------------------------------------------- deuda tecnica y riesgos


def _rule_large_files(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    huge = [(p, n) for p, n in sig.stats.largest_files if n >= FICHERO_ENORME]
    big = [(p, n) for p, n in sig.stats.largest_files if FICHERO_GRANDE <= n < FICHERO_ENORME]

    if huge:
        listing = "; ".join(f"{p} ({n} lineas)" for p, n in huge[:3])
        return [
            _f(
                FindingKind.MEJORA,
                "Ficheros desproporcionadamente grandes",
                f"{len(huge)} fichero(s) superan las {FICHERO_ENORME} lineas. Un fichero asi suele "
                "concentrar responsabilidades que deberian estar separadas, y se convierte en el punto "
                "donde todo el mundo tiene que tocar a la vez.",
                listing,
                "Medio-alto: conflictos frecuentes al integrar cambios y dificultad para probar por partes.",
            )
        ]
    if len(big) >= 3:
        return [
            _f(
                FindingKind.MEJORA,
                "Varios ficheros rozando el limite de mantenibilidad",
                f"{len(big)} ficheros superan las {FICHERO_GRANDE} lineas sin llegar a ser criticos. "
                "Conviene vigilarlos antes de que crezcan mas.",
                "; ".join(f"{p} ({n})" for p, n in big[:3]),
                "Bajo por ahora, creciente si no se divide.",
            )
        ]
    return []


def _rule_crowded_dirs(_: Signals, modules: list[ModuleNode]) -> list[Finding]:
    crowded = [m for m in modules if m.file_count >= CARPETA_SATURADA and m.path != "."]
    if not crowded:
        return []
    worst = max(crowded, key=lambda m: m.file_count)
    return [
        _f(
            FindingKind.MEJORA,
            "Carpetas saturadas de ficheros",
            f"'{worst.path}' acumula {worst.file_count} ficheros sin subdivision clara. "
            "Cuando una carpeta crece asi, encontrar el fichero correcto pasa a depender de la memoria "
            "de quien lleva tiempo en el proyecto.",
            f"{worst.path}: {worst.file_count} ficheros",
            "Bajo tecnicamente, alto para incorporar gente nueva al proyecto.",
        )
    ]


def _rule_secrets(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    findings: list[Finding] = []
    tracked_env = [p for p in sig.file_set if p.endswith(".env") or "/.env." in p or p.startswith(".env.")]
    real_env = [p for p in tracked_env if not p.endswith((".example", ".sample", ".template"))]

    if real_env:
        findings.append(
            _f(
                FindingKind.RIESGO,
                "Posible fichero de secretos en el repositorio",
                "Se ha encontrado un fichero .env con valores reales dentro del arbol analizado. "
                "Si esta versionado, las credenciales quedan en el historial de Git para siempre, "
                "aunque se borren despues.",
                ", ".join(sorted(real_env)[:3]),
                "Alto: exposicion de credenciales. Verificar .gitignore y rotar las claves afectadas.",
            )
        )
    elif sig.has_dep("dotenv", "python-dotenv", "pydantic-settings") or any(
        p.endswith(".env.example") for p in sig.file_set
    ):
        findings.append(
            _f(
                FindingKind.FORTALEZA,
                "Configuracion separada del codigo",
                "Los parametros sensibles se cargan desde variables de entorno y existe una plantilla "
                "de ejemplo. El mismo codigo sirve para desarrollo y produccion sin tocar nada.",
                ".env.example / carga de entorno declarada",
                "Reduce el riesgo de filtrar credenciales y facilita el despliegue.",
            )
        )
    return findings


def _rule_lockfile(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    if "node" not in sig.ecosystems:
        return []
    locks = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb")
    if not any(lock in sig.basenames for lock in locks):
        return [
            _f(
                FindingKind.RIESGO,
                "Sin fichero de bloqueo de dependencias",
                "No hay lockfile. Dos instalaciones en momentos distintos pueden traer versiones "
                "diferentes de las mismas librerias, asi que el entorno no es reproducible.",
                "no se encontro package-lock.json ni equivalente",
                "Alto: fallos que solo aparecen en algunos entornos y son dificiles de reproducir.",
            )
        ]
    return []


def _rule_auth_exposure(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    has_auth = any(d in AUTH_LIBS for d in (*sig.all_deps, *sig.dev_deps)) or sig.has_dir("auth")
    has_data = bool(sig.datastores)
    if has_data and not has_auth:
        return [
            _f(
                FindingKind.RIESGO,
                "Persistencia sin capa de autenticacion visible",
                "El proyecto accede a una base de datos pero no se detecta ninguna libreria ni carpeta "
                "de autenticacion. O el control de acceso vive en otro sitio, o los datos estan expuestos.",
                f"datastores: {', '.join(sig.datastores)}; sin libreria de auth",
                "Alto si se confirma: acceso no controlado a los datos.",
            )
        ]
    return []


def _rule_docs(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    if not sig.readme_path:
        return [
            _f(
                FindingKind.MEJORA,
                "Sin README en la raiz",
                "No hay documentacion de entrada. Quien llega nuevo al proyecto tiene que deducir "
                "el proposito y como arrancarlo leyendo el codigo.",
                "no se encontro README",
                "Medio: el coste de incorporacion recae entero sobre el equipo actual.",
            )
        ]
    if sig.has_dir("docs"):
        return [
            _f(
                FindingKind.FORTALEZA,
                "Documentacion mas alla del README",
                "Existe una carpeta de documentacion dedicada, senal de que el conocimiento del proyecto "
                "esta escrito y no solo en la cabeza del equipo.",
                "docs/",
                "Acelera la incorporacion y reduce la dependencia de personas concretas.",
            )
        ]
    return []


def _rule_dependency_load(sig: Signals, _: list[ModuleNode]) -> list[Finding]:
    total = len(sig.all_deps)
    if total > 60:
        return [
            _f(
                FindingKind.MEJORA,
                "Superficie de dependencias amplia",
                f"{total} dependencias de produccion declaradas. Cada una es codigo de terceros que hay "
                "que actualizar, auditar y que puede introducir vulnerabilidades.",
                f"{total} dependencias en produccion",
                "Medio: mayor carga de mantenimiento y mas superficie de ataque.",
            )
        ]
    return []


def _rule_separation(sig: Signals, modules: list[ModuleNode]) -> list[Finding]:
    layers = {m.role for m in modules}
    business = {"Servicios", "Dominio", "Casos de uso", "Logica de negocio"}
    presentation = {"Componentes de UI", "Vistas", "Plantillas", "Rutas de pagina"}
    if layers & business and layers & presentation:
        return [
            _f(
                FindingKind.FORTALEZA,
                "Separacion clara entre negocio y presentacion",
                "La logica de negocio vive en carpetas propias, separada de la interfaz. Se puede cambiar "
                "el aspecto de la aplicacion sin tocar las reglas, y al reves.",
                ", ".join(sorted((layers & business) | (layers & presentation))),
                "Permite evolucionar interfaz y negocio a ritmos distintos.",
            )
        ]
    if sig.stats.total_files > 30 and not (layers & business):
        return [
            _f(
                FindingKind.MEJORA,
                "Logica de negocio sin ubicacion explicita",
                "No se identifica ninguna carpeta dedicada a la logica de negocio. Suele significar que "
                "las reglas estan repartidas dentro de los componentes o los controladores.",
                f"carpetas observadas: {', '.join(sorted(layers)[:6])}",
                "Medio: la misma regla tiende a duplicarse en varios sitios y a divergir.",
            )
        ]
    return []


RULES: tuple[Rule, ...] = (
    _rule_tests,
    _rule_typing,
    _rule_quality_tooling,
    _rule_ci,
    _rule_containerization,
    _rule_separation,
    _rule_secrets,
    _rule_lockfile,
    _rule_auth_exposure,
    _rule_large_files,
    _rule_crowded_dirs,
    _rule_docs,
    _rule_dependency_load,
)

# Orden de presentacion: primero lo que esta bien, luego lo urgente.
_KIND_ORDER = {FindingKind.FORTALEZA: 0, FindingKind.RIESGO: 1, FindingKind.MEJORA: 2}


def diagnose(sig: Signals, modules: list[ModuleNode]) -> list[Finding]:
    """Ejecuta todas las reglas y devuelve los hallazgos ordenados."""
    findings: list[Finding] = []
    for rule in RULES:
        findings.extend(rule(sig, modules))
    findings.sort(key=lambda f: _KIND_ORDER[f.kind])
    return findings
