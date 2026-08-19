"""Mapa conceptual de modulos: que responsabilidad tiene cada carpeta clave.

No listamos ficheros. Para cada carpeta relevante deducimos su rol combinando
tres fuentes: el nombre (convenciones muy estables en la industria), lo que
contiene (extensiones dominantes) y donde esta (profundidad y padre).
"""

from __future__ import annotations

from collections import defaultdict

from classicalpy.detect.stack import Signals
from classicalpy.models import FileInfo, ModuleNode

# Nombre de carpeta -> (rol corto, proposito explicado). Convenciones del sector.
FOLDER_ROLES: dict[str, tuple[str, str]] = {
    # Punto de entrada y organizacion general
    "src": ("Codigo fuente", "Raiz del codigo escrito por el equipo, separado de configuracion y artefactos de build."),
    "app": ("Aplicacion / rutas", "Nucleo de la aplicacion. En frameworks modernos, su estructura de carpetas define directamente el mapa de URLs."),
    "pages": ("Rutas de pagina", "Cada fichero es una URL publica: el enrutado se deriva del sistema de ficheros."),
    "routes": ("Enrutado", "Declara que URL atiende cada manejador y conecta la peticion con la logica."),
    "public": ("Assets publicos", "Ficheros servidos tal cual al navegador sin pasar por el proceso de build."),
    "static": ("Assets estaticos", "Imagenes, hojas de estilo y scripts servidos directamente."),
    "assets": ("Recursos", "Imagenes, fuentes e iconos que el build procesa e incorpora al bundle."),
    # Interfaz
    "components": ("Componentes de UI", "Piezas de interfaz reutilizables. Es donde vive el vocabulario visual de la aplicacion."),
    "views": ("Vistas", "Pantallas completas que componen los componentes en una experiencia concreta."),
    "layouts": ("Plantillas de pagina", "Estructura comun (cabecera, navegacion, pie) que envuelve a las vistas."),
    "templates": ("Plantillas", "Marcado que el servidor rellena con datos antes de enviarlo al navegador."),
    "styles": ("Estilos", "Hojas de estilo, variables de diseno y tema visual."),
    "ui": ("Sistema de diseno", "Componentes base sin logica de negocio: el ladrillo comun de toda la interfaz."),
    # Logica
    "services": ("Servicios", "Logica de negocio y comunicacion con sistemas externos, aislada de la interfaz."),
    "controllers": ("Controladores", "Reciben la peticion, coordinan la logica y deciden que respuesta devolver."),
    "handlers": ("Manejadores", "Punto de entrada de cada operacion: traducen la peticion en una accion del dominio."),
    "usecases": ("Casos de uso", "Cada fichero orquesta una operacion completa del negocio de principio a fin."),
    "use-cases": ("Casos de uso", "Cada fichero orquesta una operacion completa del negocio de principio a fin."),
    "domain": ("Dominio", "Reglas y entidades del negocio, escritas sin depender de framework ni base de datos."),
    "core": ("Nucleo", "Piezas transversales de las que depende el resto: configuracion, tipos base, utilidades criticas."),
    "logic": ("Logica de negocio", "Reglas de la aplicacion separadas de la capa de presentacion."),
    "business": ("Logica de negocio", "Reglas de la aplicacion separadas de la capa de presentacion."),
    # Datos
    "models": ("Modelos de datos", "Definen la forma de las entidades y su correspondencia con la base de datos."),
    "entities": ("Entidades", "Objetos del dominio con identidad propia y ciclo de vida."),
    "schemas": ("Esquemas", "Contratos de datos: que forma deben tener las entradas y salidas de la API."),
    "repositories": ("Repositorios", "Aislan el acceso a datos: el resto del codigo pide entidades, no escribe consultas."),
    "dao": ("Acceso a datos", "Encapsula las consultas a la base de datos."),
    "migrations": ("Migraciones", "Historial versionado de los cambios del esquema de base de datos."),
    "db": ("Base de datos", "Conexion, esquema y utilidades de persistencia."),
    "database": ("Base de datos", "Conexion, esquema y utilidades de persistencia."),
    "prisma": ("Esquema de datos", "Define el modelo de datos del que se genera el cliente tipado y las migraciones."),
    "seeds": ("Datos semilla", "Datos iniciales para poblar un entorno de desarrollo o pruebas."),
    # API e integracion
    "api": ("Capa de API", "Frontera publica del sistema: define los endpoints que consumen el cliente u otros servicios."),
    "graphql": ("Esquema GraphQL", "Define tipos, consultas y mutaciones que expone la API."),
    "resolvers": ("Resolvers", "Implementan como se obtiene cada campo del esquema GraphQL."),
    "middleware": ("Middlewares", "Intercepta cada peticion para autenticar, validar, registrar o transformar antes de la logica."),
    "middlewares": ("Middlewares", "Intercepta cada peticion para autenticar, validar, registrar o transformar antes de la logica."),
    "dto": ("Objetos de transferencia", "Define la forma exacta de los datos que cruzan la frontera de la API."),
    "serializers": ("Serializadores", "Traducen entre entidades internas y el JSON que viaja por la red."),
    # Estado y utilidades de cliente
    "hooks": ("Hooks", "Logica de interfaz reutilizable extraida de los componentes."),
    "store": ("Estado global", "Estado compartido entre pantallas y su logica de actualizacion."),
    "stores": ("Estado global", "Estado compartido entre pantallas y su logica de actualizacion."),
    "context": ("Contexto de React", "Inyecta estado compartido en el arbol de componentes sin pasarlo por props."),
    "contexts": ("Contexto de React", "Inyecta estado compartido en el arbol de componentes sin pasarlo por props."),
    "reducers": ("Reductores", "Definen como cambia el estado ante cada accion."),
    "actions": ("Acciones", "Eventos que disparan cambios de estado o efectos."),
    # Soporte
    "lib": ("Librerias internas", "Codigo de apoyo propio, reutilizado por varios modulos."),
    "utils": ("Utilidades", "Funciones auxiliares sin logica de negocio."),
    "helpers": ("Utilidades", "Funciones auxiliares sin logica de negocio."),
    "config": ("Configuracion", "Parametros del entorno y ajustes del sistema, fuera del codigo de negocio."),
    "settings": ("Configuracion", "Parametros del entorno y ajustes del sistema."),
    "constants": ("Constantes", "Valores fijos compartidos, centralizados para evitar duplicarlos."),
    "types": ("Tipos", "Definiciones de tipos compartidas que documentan los contratos entre modulos."),
    "interfaces": ("Interfaces", "Contratos que las implementaciones deben cumplir."),
    "validators": ("Validacion", "Reglas que comprueban que los datos de entrada son aceptables."),
    "exceptions": ("Errores", "Tipos de error propios del dominio y su tratamiento."),
    "locales": ("Traducciones", "Textos de la interfaz en cada idioma soportado."),
    "i18n": ("Internacionalizacion", "Configuracion de idiomas y carga de traducciones."),
    # Calidad y operacion
    "tests": ("Pruebas", "Red de seguridad automatizada: verifica que el comportamiento no se rompe al cambiar el codigo."),
    "test": ("Pruebas", "Red de seguridad automatizada: verifica que el comportamiento no se rompe al cambiar el codigo."),
    "__tests__": ("Pruebas", "Pruebas colocadas junto al codigo que verifican."),
    "e2e": ("Pruebas de extremo a extremo", "Validan flujos completos de usuario sobre la aplicacion real."),
    "cypress": ("Pruebas de extremo a extremo", "Validan flujos completos de usuario en un navegador real."),
    "scripts": ("Scripts", "Automatizaciones de mantenimiento, migracion o despliegue."),
    "docs": ("Documentacion", "Explicacion del proyecto para quien se incorpora o lo consume."),
    "docker": ("Contenedores", "Definicion de las imagenes con las que se ejecuta el sistema."),
    ".github": ("Automatizacion del repositorio", "Flujos de integracion continua y plantillas de colaboracion."),
    "terraform": ("Infraestructura como codigo", "Declara los recursos de nube de forma versionada."),
    "packages": ("Paquetes del monorepo", "Cada subcarpeta es una unidad publicable con su propio ciclo de vida."),
    "apps": ("Aplicaciones del monorepo", "Cada subcarpeta es una aplicacion desplegable independiente."),
    # Separacion cliente/servidor
    "client": ("Cliente", "Todo el codigo que se ejecuta en el navegador del usuario."),
    "frontend": ("Frontend", "Interfaz de usuario, desplegada de forma independiente del servidor."),
    "server": ("Servidor", "Codigo que atiende peticiones, aplica la logica y accede a los datos."),
    "backend": ("Backend", "Codigo que atiende peticiones, aplica la logica y accede a los datos."),
    "worker": ("Procesos en segundo plano", "Ejecuta tareas fuera del ciclo de peticion HTTP."),
    "workers": ("Procesos en segundo plano", "Ejecuta tareas fuera del ciclo de peticion HTTP."),
    "jobs": ("Tareas programadas", "Trabajos que se ejecutan periodicamente o en diferido."),
    # Etapas de un pipeline de procesamiento
    "ingest": ("Ingesta", "Punto de entrada de los datos externos al sistema, antes de cualquier procesado."),
    "ingestion": ("Ingesta", "Punto de entrada de los datos externos al sistema."),
    "detect": ("Deteccion", "Extrae senales y clasifica la entrada para que las etapas siguientes decidan."),
    "analyze": ("Analisis", "Transforma las senales detectadas en conclusiones."),
    "analysis": ("Analisis", "Transforma los datos en conclusiones."),
    "parsers": ("Parseo", "Convierte formatos externos en las estructuras internas del sistema."),
    "parse": ("Parseo", "Convierte formatos externos en las estructuras internas del sistema."),
    "transform": ("Transformacion", "Adapta los datos entre la forma de origen y la de destino."),
    "pipeline": ("Orquestacion", "Encadena las etapas del proceso; es donde se ve el flujo completo."),
    "report": ("Presentacion", "Serializa el resultado al formato que consume el destinatario."),
    "reports": ("Presentacion", "Serializa el resultado al formato que consume el destinatario."),
    "reporting": ("Presentacion", "Serializa el resultado al formato que consume el destinatario."),
    "renderers": ("Presentacion", "Convierte el resultado interno en la salida visible."),
    "exporters": ("Exportacion", "Vuelca el resultado a formatos o sistemas externos."),
    "adapters": ("Adaptadores", "Traducen entre el dominio y los sistemas externos, sin contaminar las reglas de negocio."),
    "ports": ("Puertos", "Interfaces que el dominio define y la infraestructura implementa."),
    "infrastructure": ("Infraestructura", "Implementaciones concretas de acceso a base de datos, red y sistemas externos."),
    "cli": ("Interfaz de terminal", "Expone la funcionalidad como comandos ejecutables desde la consola."),
    "web": ("Interfaz web", "Expone la funcionalidad por HTTP: API y/o paginas para el navegador."),
    "cmd": ("Puntos de entrada", "Ejecutables del proyecto, uno por binario."),
}

# Lenguaje dominante -> rol de respaldo cuando el nombre de carpeta no dice nada.
_CONTENT_FALLBACK: dict[str, tuple[str, str]] = {
    "TypeScript": ("Modulo de aplicacion", "Codigo de aplicacion tipado; su responsabilidad no se deduce del nombre de la carpeta."),
    "JavaScript": ("Modulo de aplicacion", "Codigo de aplicacion; su responsabilidad no se deduce del nombre de la carpeta."),
    "Python": ("Modulo Python", "Codigo de aplicacion; su responsabilidad no se deduce del nombre de la carpeta."),
    "CSS": ("Estilos", "Hojas de estilo del proyecto."),
    "HTML": ("Marcado", "Paginas o fragmentos HTML."),
    "Markdown": ("Documentacion", "Textos explicativos del proyecto."),
    "SQL": ("Persistencia", "Consultas, esquemas o migraciones de base de datos."),
}

MIN_FILES_FOR_MODULE = 2
MAX_MODULES = 22


def build_modules(sig: Signals, max_depth: int = 3) -> list[ModuleNode]:
    """Devuelve las carpetas clave del proyecto con su responsabilidad inferida.

    Se descartan las carpetas irrelevantes (muy pocos ficheros y nombre no
    reconocido) para que el mapa quepa en la cabeza de quien lo lee.
    """
    by_dir: dict[str, list[FileInfo]] = defaultdict(list)
    for info in sig.files:
        parts = info.path.split("/")
        if len(parts) == 1:
            by_dir["."].append(info)
            continue
        for depth in range(1, min(len(parts), max_depth + 1)):
            by_dir["/".join(parts[:depth])].append(info)

    modules: list[ModuleNode] = []
    for path, contents in by_dir.items():
        node = _describe_dir(path, contents)
        if node is not None:
            modules.append(node)

    # Una carpeta puramente contenedora (src/) no aporta si su unico hijo ya sale.
    modules = _drop_redundant_wrappers(modules)
    # La raiz siempre primero; luego por profundidad y por volumen, para que el
    # mapa se lea de lo general a lo particular.
    modules.sort(key=lambda m: (m.path != ".", m.path.count("/"), -m.file_count, m.path))
    return modules[:MAX_MODULES]


def _describe_dir(path: str, contents: list[FileInfo]) -> ModuleNode | None:
    name = path.rsplit("/", 1)[-1].lower()
    known = FOLDER_ROLES.get(name)

    if known is None and len(contents) < MIN_FILES_FOR_MODULE:
        return None
    if path == ".":
        known = ("Raiz del proyecto", "Manifiestos, configuracion y documentacion de entrada al repositorio.")

    languages = _dominant_languages(contents)
    if known is None:
        primary = languages[0] if languages else ""
        known = _CONTENT_FALLBACK.get(
            primary, ("Modulo", "Agrupa ficheros relacionados sin una convencion de nombre reconocible.")
        )

    role, purpose = known
    return ModuleNode(
        path=path,
        role=role,
        purpose=purpose,
        file_count=len(contents),
        languages=languages,
        key_files=_key_files(contents),
    )


def _dominant_languages(contents: list[FileInfo]) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for info in contents:
        counts[info.language] += 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return [language for language, _ in ranked[:3]]


# Nombres que casi siempre son el punto de entrada o el contrato del modulo.
_ENTRY_HINTS = ("index", "main", "app", "__init__", "server", "routes", "schema", "config")


def _key_files(contents: list[FileInfo], limit: int = 4) -> list[str]:
    """Elige los ficheros que mejor explican el modulo: entradas y los mas grandes."""
    entries = [f for f in contents if f.name.rsplit(".", 1)[0].lower() in _ENTRY_HINTS]
    rest = sorted(
        (f for f in contents if f not in entries and not f.is_config),
        key=lambda f: f.lines,
        reverse=True,
    )
    picked: list[str] = []
    for info in [*entries, *rest]:
        if info.path not in picked:
            picked.append(info.path)
        if len(picked) >= limit:
            break
    return picked


def _drop_redundant_wrappers(modules: list[ModuleNode]) -> list[ModuleNode]:
    """Quita carpetas que solo envuelven a otra con el mismo contenido.

    Si 'src/' y 'src/app/' tienen el mismo numero de ficheros, 'src/' no aporta
    informacion propia y solo alarga el mapa.
    """
    by_path = {m.path: m for m in modules}
    redundant: set[str] = set()
    for module in modules:
        children = [m for m in modules if m.path.startswith(module.path + "/") and m.path.count("/") == module.path.count("/") + 1]
        if len(children) == 1 and children[0].file_count == module.file_count:
            # El envoltorio no aporta salvo que su propio nombre sea informativo.
            if module.path.rsplit("/", 1)[-1].lower() in {"src", "lib", "app"} and module.path != ".":
                redundant.add(module.path)
    return [m for p, m in by_path.items() if p not in redundant]
