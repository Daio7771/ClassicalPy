"""Reconstruccion del flujo principal: de la interfaz al dato y vuelta.

Segun el patron arquitectonico detectado, el recorrido de una peticion cambia
por completo. Cada constructor de flujo describe ese recorrido para una familia
de arquitecturas, y solo incluye los pasos que tienen evidencia real.
"""

from __future__ import annotations

from classicalpy.detect.stack import Signals
from classicalpy.models import FlowStep

# Patrones que describen la *topologia* del repositorio, no el recorrido de una
# peticion: un monorepo no tiene un flujo propio, lo tiene el stack que contiene.
_PATRONES_DE_TOPOLOGIA = ("monorepo", "microservicios", "capas", "hexagonal")


def build_flow(sig: Signals, architecture_pattern: str) -> list[FlowStep]:
    """Traza el recorrido de una peticion de punta a punta."""
    pattern = architecture_pattern.lower()

    if any(marca in pattern for marca in _PATRONES_DE_TOPOLOGIA):
        steps = _flow_by_stack(sig)
    elif "renderizado en servidor" in pattern:
        steps = _flow_meta_framework(sig)
    elif "cliente-servidor" in pattern or "spa" in pattern:
        steps = _flow_spa(sig)
    elif "mvc" in pattern:
        steps = _flow_mvc(sig)
    elif "monolito" in pattern:
        steps = _flow_monolito(sig)
    elif "api" in pattern and "servicio" in pattern:
        steps = _flow_api_only(sig)
    elif "estatico" in pattern or "jamstack" in pattern:
        steps = _flow_static(sig)
    else:
        steps = _flow_by_stack(sig)

    for index, step in enumerate(steps, start=1):
        step.order = index
    return steps


def _flow_by_stack(sig: Signals) -> list[FlowStep]:
    """Elige el flujo por las tecnologias presentes, no por el patron.

    Se usa cuando el patron detectado no dice nada sobre el recorrido de una
    peticion, y como ultimo respaldo.
    """
    if sig.meta_frameworks:
        return _flow_meta_framework(sig)
    if sig.frontends and sig.backends:
        return _flow_spa(sig)
    if sig.has_dir("controllers") or sig.has_dep("django", "rails", "laravel/framework"):
        return _flow_mvc(sig)
    if sig.backends and sig.has_dir("templates", "views", "public", "static"):
        return _flow_monolito(sig)
    if sig.backends:
        return _flow_api_only(sig)
    if sig.frontends:
        return _flow_spa(sig)
    if sig.stats.files_by_language.get("HTML", 0) > 0:
        return _flow_static(sig)
    return _flow_generic(sig)


def _step(actor: str, title: str, detail: str, evidence: str | None = None) -> FlowStep:
    return FlowStep(order=0, actor=actor, title=title, detail=detail, evidence=evidence)


# ------------------------------------------------------------------ constructores


def _flow_meta_framework(sig: Signals) -> list[FlowStep]:
    framework = sig.meta_frameworks[0] if sig.meta_frameworks else "el framework"
    route_dir = "app/" if sig.has_dir("app") else ("pages/" if sig.has_dir("pages") else "el enrutador")

    steps = [
        _step(
            "Usuario",
            "Solicita una URL",
            "La persona abre una direccion en el navegador o hace clic en un enlace interno.",
        ),
        _step(
            "Servidor",
            f"{framework} resuelve la ruta",
            f"El framework busca en '{route_dir}' el fichero que corresponde a esa URL. "
            "La estructura de carpetas ES la tabla de rutas: no hay configuracion intermedia.",
            route_dir,
        ),
    ]
    steps.extend(_auth_step(sig))
    steps.extend(_data_steps(sig))
    steps.append(
        _step(
            "Servidor",
            "Renderiza el HTML",
            "Con los datos ya resueltos, el componente de pagina se renderiza en el servidor y "
            "se envia HTML completo. El navegador muestra contenido sin esperar a JavaScript.",
        )
    )
    steps.append(
        _step(
            "Navegador",
            "Hidrata la interfaz",
            "El JavaScript del cliente toma el control del HTML ya pintado y activa la "
            "interactividad (formularios, navegacion, estado local).",
        )
    )
    steps.extend(_mutation_step(sig))
    return steps


def _flow_spa(sig: Signals) -> list[FlowStep]:
    front = ", ".join(sig.frontends) or "la aplicacion de cliente"
    back = ", ".join(sig.backends) or "el servidor"
    steps = [
        _step(
            "Usuario",
            "Interactua con la interfaz",
            f"La accion ocurre en {front}, que ya esta cargado en el navegador: no hay recarga de pagina.",
        ),
        _step(
            "Cliente",
            "Lanza una peticion a la API",
            "El cliente HTTP envia la peticion al backend, adjuntando el token o cookie de sesion."
            + (f" Se usa {_http_client(sig)}." if _http_client(sig) else ""),
            _http_client(sig),
        ),
        _step(
            "Servidor",
            f"{back} recibe y enruta la peticion",
            "El router localiza el manejador del endpoint y encadena los middlewares "
            "(CORS, logging, autenticacion) antes de ejecutar la logica.",
        ),
    ]
    steps.extend(_auth_step(sig))
    steps.extend(_validation_step(sig))
    steps.extend(_data_steps(sig))
    steps.append(
        _step(
            "Servidor",
            "Devuelve la respuesta serializada",
            "El resultado se convierte a JSON con la forma que espera el contrato de la API.",
        )
    )
    steps.append(
        _step(
            "Cliente",
            "Actualiza el estado y repinta",
            "La respuesta entra en el estado de la aplicacion y solo los componentes afectados se vuelven a renderizar."
            + (f" Gestionado por {_state_lib(sig)}." if _state_lib(sig) else ""),
            _state_lib(sig),
        )
    )
    return steps


def _flow_mvc(sig: Signals) -> list[FlowStep]:
    steps = [
        _step("Usuario", "Solicita una URL", "El navegador pide una pagina al servidor."),
        _step(
            "Servidor",
            "El enrutador elige el controlador",
            "La tabla de rutas asocia la URL y el verbo HTTP con un metodo de controlador concreto.",
            "routes/" if sig.has_dir("routes") else None,
        ),
    ]
    steps.extend(_auth_step(sig))
    steps.extend(_validation_step(sig))
    steps.append(
        _step(
            "Controlador",
            "Coordina la operacion",
            "El controlador no contiene reglas de negocio: pide los datos a los modelos o servicios "
            "y decide que vista se renderiza.",
            "controllers/" if sig.has_dir("controllers") else None,
        )
    )
    steps.extend(_data_steps(sig))
    steps.append(
        _step(
            "Vista",
            "Renderiza la plantilla",
            "La plantilla recibe los datos y produce el HTML final que se envia al navegador.",
            "templates/" if sig.has_dir("templates") else ("views/" if sig.has_dir("views") else None),
        )
    )
    return steps


def _flow_api_only(sig: Signals) -> list[FlowStep]:
    back = ", ".join(sig.backends) or "el servidor"
    steps = [
        _step(
            "Sistema cliente",
            "Llama a un endpoint",
            "Otra aplicacion o servicio envia una peticion HTTP con su credencial de acceso.",
        ),
        _step(
            "Servidor",
            f"{back} enruta la peticion",
            "El framework localiza el manejador declarado para esa ruta y ejecuta la cadena de middlewares.",
        ),
    ]
    steps.extend(_auth_step(sig))
    steps.extend(_validation_step(sig))
    steps.append(
        _step(
            "Logica de negocio",
            "Ejecuta la operacion",
            "El caso de uso aplica las reglas del dominio sobre los datos ya validados.",
            "services/" if sig.has_dir("services") else None,
        )
    )
    steps.extend(_data_steps(sig))
    steps.append(
        _step(
            "Servidor",
            "Responde en JSON",
            "El resultado se serializa segun el esquema de salida y se devuelve con su codigo de estado.",
        )
    )
    return steps


def _flow_monolito(sig: Signals) -> list[FlowStep]:
    """Un mismo servidor entrega la interfaz y atiende sus llamadas."""
    back = ", ".join(sig.backends) or "el servidor"
    vista = next((d for d in ("templates", "views", "public", "static") if sig.has_dir(d)), "static")

    steps = [
        _step(
            "Usuario",
            "Abre la aplicacion",
            f"El navegador pide la pagina y {back} le devuelve la interfaz desde '{vista}/'. "
            "No hay un servidor de frontend aparte.",
            f"{vista}/",
        ),
        _step(
            "Navegador",
            "Envia la accion del usuario",
            "El JavaScript de la pagina llama a un endpoint del mismo servidor con los datos del formulario.",
        ),
        _step(
            "Servidor",
            f"{back} enruta la llamada",
            "El framework localiza el manejador de esa ruta y ejecuta la cadena de middlewares antes de la logica.",
        ),
    ]
    steps.extend(_auth_step(sig))
    steps.extend(_validation_step(sig))
    steps.append(
        _step(
            "Logica de negocio",
            "Ejecuta la operacion",
            "Se aplican las reglas del dominio sobre los datos ya validados.",
            "services/" if sig.has_dir("services") else None,
        )
    )
    steps.extend(_data_steps(sig))
    steps.append(
        _step(
            "Navegador",
            "Pinta el resultado",
            "La respuesta vuelve a la misma pagina, que actualiza solo la parte afectada sin recargar.",
        )
    )
    return steps


def _flow_static(sig: Signals) -> list[FlowStep]:
    return [
        _step(
            "Desarrollo",
            "Se ejecuta el build",
            "El generador convierte plantillas y contenido en ficheros HTML, CSS y JS definitivos.",
            next(iter(k for k in sig.scripts if "build" in k), None),
        ),
        _step(
            "Despliegue",
            "Los ficheros se publican en la CDN",
            "El resultado del build se sube a una red de distribucion. No hay servidor de aplicacion en produccion.",
        ),
        _step(
            "Usuario",
            "Solicita una pagina",
            "La CDN devuelve el fichero ya generado desde el nodo mas cercano: la respuesta es casi inmediata.",
        ),
        _step(
            "Navegador",
            "Ejecuta la interactividad",
            "El JavaScript incluido activa las partes dinamicas y, si las hay, llama a APIs externas.",
        ),
    ]


def _flow_generic(sig: Signals) -> list[FlowStep]:
    steps = [
        _step(
            "Entrada",
            "Llega una peticion o invocacion",
            "El punto de entrada del proyecto recibe la solicitud."
            + (f" Punto de entrada probable: {_entry_point(sig)}." if _entry_point(sig) else ""),
            _entry_point(sig),
        ),
        _step(
            "Aplicacion",
            "Se ejecuta la logica",
            "El codigo de aplicacion procesa la entrada segun las reglas del proyecto.",
        ),
    ]
    steps.extend(_data_steps(sig))
    steps.append(
        _step("Salida", "Se devuelve el resultado", "El resultado se entrega al consumidor de la operacion.")
    )
    return steps


# --------------------------------------------------------------- pasos opcionales


def _auth_step(sig: Signals) -> list[FlowStep]:
    from classicalpy.detect.stack import AUTH_LIBS

    present = sorted({d for d in (*sig.all_deps, *sig.dev_deps) if d in AUTH_LIBS})
    if not present and not sig.has_dir("auth"):
        return []
    return [
        _step(
            "Seguridad",
            "Se verifica la identidad",
            "Antes de tocar ningun dato se comprueba quien hace la peticion y si tiene permiso. "
            "Una peticion sin credencial valida se corta aqui.",
            ", ".join(present) or "carpeta auth/",
        )
    ]


def _validation_step(sig: Signals) -> list[FlowStep]:
    validators = [d for d in ("zod", "yup", "joi", "pydantic", "class-validator", "marshmallow", "ajv") if sig.has_dep(d)]
    if not validators and not sig.has_dir("schemas", "validators"):
        return []
    return [
        _step(
            "Validacion",
            "Se comprueba la forma de los datos",
            "La entrada se contrasta con un esquema declarado. Si no encaja, se rechaza con un error "
            "descriptivo antes de llegar a la logica de negocio.",
            ", ".join(validators) or "schemas/",
        )
    ]


def _data_steps(sig: Signals) -> list[FlowStep]:
    if not sig.datastores and not sig.has_dir("models", "repositories", "db", "database"):
        return []
    engine = ", ".join(sig.datastores) or "la capa de datos"
    steps = [
        _step(
            "Persistencia",
            f"Se consulta o modifica el dato via {engine}",
            "El acceso a la base de datos esta encapsulado: la logica de negocio pide entidades, "
            "no escribe SQL directamente. Aqui es donde suelen aparecer los cuellos de botella.",
            engine,
        )
    ]
    if sig.has_dep("redis", "ioredis"):
        steps.insert(
            0,
            _step(
                "Cache",
                "Se busca primero en cache",
                "Si el dato esta en memoria se devuelve sin tocar la base de datos, ahorrando la consulta mas cara.",
                "redis",
            ),
        )
    if sig.has_dep("celery", "bullmq"):
        steps.append(
            _step(
                "Segundo plano",
                "El trabajo pesado se encola",
                "Las tareas lentas (correo, informes, procesado) salen del ciclo de peticion y se ejecutan "
                "en un worker aparte, para que el usuario no espere.",
                "celery" if sig.has_dep("celery") else "bullmq",
            )
        )
    return steps


def _mutation_step(sig: Signals) -> list[FlowStep]:
    if not (sig.has_dir("api") or sig.path_contains("/api/")):
        return []
    return [
        _step(
            "Servidor",
            "Atiende las mutaciones",
            "Los envios de formulario y acciones del usuario llegan a las rutas de API del mismo proyecto, "
            "que escriben en la base de datos y devuelven el estado actualizado.",
            "api/",
        )
    ]


# ------------------------------------------------------------------- utilidades


def _http_client(sig: Signals) -> str | None:
    for name in ("axios", "@tanstack/react-query", "swr", "apollo-client", "httpx", "requests"):
        if sig.has_dep(name):
            return name
    return None


def _state_lib(sig: Signals) -> str | None:
    for name in ("@reduxjs/toolkit", "redux", "zustand", "jotai", "mobx", "pinia"):
        if sig.has_dep(name):
            return name
    return None


_ENTRY_CANDIDATES = (
    "main.py", "app.py", "__main__.py", "manage.py", "wsgi.py", "asgi.py",
    "index.js", "index.ts", "server.js", "server.ts", "main.ts", "main.go", "main.rs",
)


def _entry_point(sig: Signals) -> str | None:
    for candidate in _ENTRY_CANDIDATES:
        if candidate in sig.basenames:
            return candidate
    return None
