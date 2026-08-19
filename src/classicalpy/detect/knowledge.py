"""Base de conocimiento curada: dependencia -> que papel juega en un proyecto.

Es lo que permite escribir la columna "Rol en este Proyecto" sin llamar a
ninguna API: en vez de repetir la descripcion oficial del paquete, explicamos
la funcion estrategica que cumple dentro de una arquitectura web.

Cada entrada es: nombre -> (categoria, rol).
"""

from __future__ import annotations

# ---------------------------------------------------------------- ecosistema JS
_NODE: dict[str, tuple[str, str]] = {
    # Frameworks de aplicacion
    "next": ("Framework fullstack", "Orquesta el renderizado (SSR/SSG), el enrutado por ficheros y las rutas de API en un solo proceso."),
    "nuxt": ("Framework fullstack", "Capa fullstack sobre Vue: renderizado en servidor, enrutado automatico y endpoints de API."),
    "remix": ("Framework fullstack", "Gestiona carga de datos y mutaciones acopladas a la ruta, con renderizado en servidor."),
    "@sveltejs/kit": ("Framework fullstack", "Enrutado, carga de datos y endpoints de servidor para aplicaciones Svelte."),
    "astro": ("Framework de contenido", "Genera paginas estaticas enviando cero JavaScript por defecto; hidrata solo los componentes interactivos."),
    "gatsby": ("Framework estatico", "Compila el sitio a HTML estatico en tiempo de build a partir de fuentes de datos."),
    "express": ("Framework de servidor", "Define las rutas HTTP y encadena los middlewares que procesan cada peticion."),
    "fastify": ("Framework de servidor", "Servidor HTTP orientado a rendimiento con validacion de esquemas integrada."),
    "koa": ("Framework de servidor", "Servidor HTTP minimalista basado en middlewares asincronos."),
    "@nestjs/core": ("Framework de servidor", "Impone una arquitectura modular con inyeccion de dependencias al estilo Angular/Spring."),
    "hono": ("Framework de servidor", "Router HTTP ligero pensado para entornos edge y serverless."),
    "@hapi/hapi": ("Framework de servidor", "Servidor HTTP con configuracion declarativa de rutas y validacion."),
    # Capa de vista
    "react": ("Libreria UI", "Construye la interfaz como un arbol de componentes con estado y re-renderizado declarativo."),
    "react-dom": ("Libreria UI", "Conecta el arbol de componentes React con el DOM del navegador."),
    "vue": ("Libreria UI", "Construye la interfaz con componentes reactivos de sintaxis declarativa."),
    "svelte": ("Libreria UI", "Compila los componentes a JavaScript imperativo sin DOM virtual en tiempo de ejecucion."),
    "@angular/core": ("Framework UI", "Framework de front-end completo con inyeccion de dependencias, plantillas y enrutado."),
    "solid-js": ("Libreria UI", "Interfaz reactiva de grano fino sin DOM virtual."),
    "preact": ("Libreria UI", "Alternativa ligera a React con la misma API."),
    "htmx": ("Libreria UI", "Anade interactividad al HTML mediante atributos, devolviendo fragmentos desde el servidor."),
    "alpinejs": ("Libreria UI", "Interactividad ligera declarada directamente en el marcado."),
    # Enrutado y estado en cliente
    "react-router-dom": ("Enrutado", "Traduce la URL del navegador al componente de pantalla correspondiente."),
    "vue-router": ("Enrutado", "Mapea rutas del navegador a vistas Vue."),
    "redux": ("Gestion de estado", "Centraliza el estado de la aplicacion en un unico almacen con mutaciones explicitas."),
    "@reduxjs/toolkit": ("Gestion de estado", "Estado centralizado con menos boilerplate: slices, thunks y cache de peticiones."),
    "zustand": ("Gestion de estado", "Estado global ligero basado en hooks, sin contexto ni boilerplate."),
    "jotai": ("Gestion de estado", "Estado global atomico y granular."),
    "mobx": ("Gestion de estado", "Estado observable que propaga cambios automaticamente a la vista."),
    "pinia": ("Gestion de estado", "Almacen de estado oficial para aplicaciones Vue."),
    "@tanstack/react-query": ("Datos remotos", "Cachea, revalida y sincroniza los datos del servidor en el cliente."),
    "swr": ("Datos remotos", "Cache y revalidacion automatica de peticiones en el cliente."),
    "apollo-client": ("Datos remotos", "Cliente GraphQL con cache normalizada."),
    # Cliente HTTP y API
    "axios": ("Cliente HTTP", "Realiza las llamadas al backend y centraliza cabeceras, errores e interceptores."),
    "graphql": ("Capa de API", "Define el esquema de tipos que expone el backend a los consumidores."),
    "@apollo/server": ("Capa de API", "Sirve el esquema GraphQL y resuelve las consultas entrantes."),
    "@trpc/server": ("Capa de API", "Define procedimientos tipados que el cliente consume sin generar codigo."),
    "socket.io": ("Tiempo real", "Mantiene un canal bidireccional persistente entre navegador y servidor."),
    "ws": ("Tiempo real", "Implementacion de WebSocket de bajo nivel para comunicacion persistente."),
    # Persistencia
    "prisma": ("ORM", "Genera un cliente tipado a partir del esquema y gestiona las migraciones de la base de datos."),
    "@prisma/client": ("ORM", "Cliente de acceso a datos tipado generado desde el esquema Prisma."),
    "typeorm": ("ORM", "Mapea clases TypeScript a tablas y gestiona migraciones."),
    "sequelize": ("ORM", "Mapea modelos JavaScript a tablas SQL."),
    "mongoose": ("ODM", "Impone esquemas y validacion sobre las colecciones de MongoDB."),
    "drizzle-orm": ("ORM", "Consultas SQL tipadas en TypeScript, cercanas al SQL real."),
    "knex": ("Query builder", "Construye consultas SQL programaticamente y gestiona migraciones."),
    "pg": ("Driver de BD", "Conexion de bajo nivel con PostgreSQL."),
    "mysql2": ("Driver de BD", "Conexion de bajo nivel con MySQL/MariaDB."),
    "mongodb": ("Driver de BD", "Conexion de bajo nivel con MongoDB."),
    "ioredis": ("Cache / cola", "Cliente de Redis para cache, sesiones o pub/sub."),
    "better-sqlite3": ("Base de datos", "Base de datos SQL embebida en el propio proceso."),
    "@supabase/supabase-js": ("Backend gestionado", "Da acceso a base de datos, autenticacion y almacenamiento alojados."),
    "firebase": ("Backend gestionado", "Provee base de datos en tiempo real, autenticacion y hosting gestionados."),
    # Autenticacion y seguridad
    "next-auth": ("Autenticacion", "Gestiona el inicio de sesion, los proveedores externos y la sesion del usuario."),
    "passport": ("Autenticacion", "Encadena estrategias de autenticacion sobre el servidor HTTP."),
    "jsonwebtoken": ("Autenticacion", "Firma y verifica los tokens que acreditan la identidad en cada peticion."),
    "bcrypt": ("Seguridad", "Deriva y verifica hashes de contrasena resistentes a fuerza bruta."),
    "bcryptjs": ("Seguridad", "Hash de contrasenas en JavaScript puro."),
    "helmet": ("Seguridad", "Endurece las cabeceras HTTP de respuesta frente a ataques comunes."),
    "cors": ("Seguridad", "Controla que origenes externos pueden consumir la API."),
    "@clerk/nextjs": ("Autenticacion", "Externaliza registro, login y gestion de sesiones a un servicio."),
    # Validacion
    "zod": ("Validacion", "Valida y tipa los datos que entran desde formularios, API o entorno."),
    "yup": ("Validacion", "Define esquemas de validacion para formularios y payloads."),
    "joi": ("Validacion", "Valida los cuerpos de peticion antes de que lleguen a la logica de negocio."),
    "class-validator": ("Validacion", "Valida DTOs mediante decoradores sobre las clases."),
    "ajv": ("Validacion", "Valida datos contra esquemas JSON Schema."),
    # Estilos
    "tailwindcss": ("Estilos", "Sistema de clases utilitarias que define el diseno directamente en el marcado."),
    "styled-components": ("Estilos", "Encapsula el CSS dentro de cada componente en tiempo de ejecucion."),
    "@emotion/react": ("Estilos", "CSS-in-JS con estilos acoplados al componente."),
    "sass": ("Estilos", "Preprocesador que anade variables y anidamiento al CSS."),
    "bootstrap": ("Estilos", "Sistema de rejilla y componentes visuales predefinidos."),
    "@mui/material": ("Componentes UI", "Biblioteca de componentes visuales con Material Design."),
    "antd": ("Componentes UI", "Biblioteca de componentes de interfaz para paneles de administracion."),
    "@chakra-ui/react": ("Componentes UI", "Componentes accesibles y tematizables."),
    "framer-motion": ("Animacion", "Declara las animaciones y transiciones de la interfaz."),
    # Build y tooling
    "vite": ("Build", "Sirve el proyecto en desarrollo y lo empaqueta optimizado para produccion."),
    "webpack": ("Build", "Empaqueta modulos y assets en los bundles que consume el navegador."),
    "esbuild": ("Build", "Transpila y empaqueta a gran velocidad."),
    "rollup": ("Build", "Empaqueta librerias con tree-shaking agresivo."),
    "parcel": ("Build", "Empaquetador sin configuracion."),
    "turbo": ("Monorepo", "Cachea y paraleliza las tareas de build entre paquetes del monorepo."),
    "nx": ("Monorepo", "Orquesta builds, tests y dependencias entre proyectos del monorepo."),
    "lerna": ("Monorepo", "Gestiona versionado y publicacion de paquetes del monorepo."),
    "typescript": ("Lenguaje", "Anade tipado estatico: los errores de contrato se detectan antes de ejecutar."),
    "eslint": ("Calidad", "Detecta errores y aplica convenciones de codigo de forma automatica."),
    "prettier": ("Calidad", "Normaliza el formato del codigo para eliminar discusiones de estilo."),
    "husky": ("Calidad", "Ejecuta comprobaciones automaticas antes de cada commit."),
    # Testing
    "jest": ("Testing", "Ejecuta la suite de pruebas unitarias y mide la cobertura."),
    "vitest": ("Testing", "Motor de pruebas unitarias integrado con Vite."),
    "mocha": ("Testing", "Ejecuta las pruebas unitarias del backend."),
    "@playwright/test": ("Testing E2E", "Automatiza un navegador real para validar los flujos completos de usuario."),
    "cypress": ("Testing E2E", "Prueba la aplicacion en un navegador real simulando al usuario."),
    "supertest": ("Testing", "Lanza peticiones HTTP contra la API dentro de las pruebas."),
    # Infra y operacion
    "dotenv": ("Configuracion", "Carga la configuracion sensible desde variables de entorno, fuera del codigo."),
    "winston": ("Observabilidad", "Centraliza los logs de la aplicacion y su enrutado a destinos externos."),
    "pino": ("Observabilidad", "Registro de logs estructurados de alto rendimiento."),
    "bullmq": ("Cola de trabajos", "Encola tareas pesadas para ejecutarlas fuera del ciclo de peticion."),
    "nodemailer": ("Integracion", "Envia correo transaccional desde el servidor."),
    "stripe": ("Pagos", "Procesa cobros y suscripciones delegando el dato sensible de tarjeta."),
    "aws-sdk": ("Infraestructura", "Habla con los servicios de AWS (almacenamiento, colas, funciones)."),
    # Utilidades frecuentes
    "lodash": ("Utilidad", "Coleccion de funciones auxiliares para manipular datos."),
    "date-fns": ("Utilidad", "Manipula y formatea fechas de forma inmutable."),
    "dayjs": ("Utilidad", "Manipulacion ligera de fechas."),
    "moment": ("Utilidad", "Manipulacion de fechas (libreria en modo mantenimiento)."),
    "uuid": ("Utilidad", "Genera identificadores unicos sin coordinacion central."),
    "i18next": ("Internacionalizacion", "Gestiona las traducciones y el idioma activo de la interfaz."),
    "react-hook-form": ("Formularios", "Gestiona estado, validacion y envio de formularios con minimos re-renderizados."),
    "chart.js": ("Visualizacion", "Dibuja los graficos de datos de la interfaz."),
    "d3": ("Visualizacion", "Construye visualizaciones de datos a medida sobre SVG."),
    "puppeteer": ("Automatizacion", "Controla un navegador sin interfaz para scraping o generacion de PDF."),
    "cheerio": ("Automatizacion", "Parsea y consulta HTML en servidor con sintaxis tipo jQuery."),
}

# ------------------------------------------------------------ ecosistema Python
_PYTHON: dict[str, tuple[str, str]] = {
    "django": ("Framework fullstack", "Aporta ORM, panel de administracion, enrutado y plantillas en un solo framework."),
    "djangorestframework": ("Capa de API", "Expone los modelos de Django como una API REST con serializacion y permisos."),
    "flask": ("Framework de servidor", "Micro-framework que define las rutas HTTP y delega el resto en extensiones."),
    "fastapi": ("Framework de API", "Define endpoints tipados, valida las entradas y genera la documentacion OpenAPI sola."),
    "starlette": ("Framework de servidor", "Nucleo ASGI asincrono sobre el que se apoya FastAPI."),
    "uvicorn": ("Servidor", "Servidor ASGI que ejecuta la aplicacion y atiende las conexiones HTTP."),
    "gunicorn": ("Servidor", "Gestiona los procesos worker que sirven la aplicacion en produccion."),
    "tornado": ("Framework de servidor", "Servidor asincrono orientado a conexiones de larga duracion."),
    "sanic": ("Framework de servidor", "Servidor HTTP asincrono orientado a rendimiento."),
    "litestar": ("Framework de API", "Framework ASGI tipado con inyeccion de dependencias."),
    "pydantic": ("Validacion", "Valida y convierte los datos de entrada segun anotaciones de tipo."),
    "pydantic-settings": ("Configuracion", "Carga y valida la configuracion desde variables de entorno."),
    "marshmallow": ("Validacion", "Serializa y valida objetos de dominio hacia/desde JSON."),
    "sqlalchemy": ("ORM", "Mapea clases Python a tablas y construye las consultas SQL."),
    "alembic": ("Migraciones", "Versiona los cambios del esquema de base de datos."),
    "psycopg2-binary": ("Driver de BD", "Conexion de bajo nivel con PostgreSQL."),
    "psycopg": ("Driver de BD", "Conexion de bajo nivel con PostgreSQL."),
    "asyncpg": ("Driver de BD", "Conexion asincrona con PostgreSQL."),
    "pymongo": ("Driver de BD", "Conexion con MongoDB."),
    "redis": ("Cache / cola", "Almacen en memoria para cache, sesiones o colas."),
    "celery": ("Cola de trabajos", "Ejecuta tareas pesadas en segundo plano, fuera del ciclo de peticion."),
    "requests": ("Cliente HTTP", "Realiza las llamadas salientes a servicios externos."),
    "httpx": ("Cliente HTTP", "Cliente HTTP con soporte asincrono para llamadas a terceros."),
    "aiohttp": ("Cliente HTTP", "Cliente y servidor HTTP asincronos."),
    "jinja2": ("Plantillas", "Renderiza el HTML final inyectando los datos en las plantillas."),
    "beautifulsoup4": ("Automatizacion", "Parsea y extrae informacion de documentos HTML."),
    "pandas": ("Datos", "Manipula y agrega conjuntos de datos tabulares."),
    "numpy": ("Datos", "Calculo numerico vectorizado sobre arrays."),
    "pytest": ("Testing", "Ejecuta la suite de pruebas del proyecto."),
    "ruff": ("Calidad", "Analiza el codigo y aplica convenciones de estilo a gran velocidad."),
    "black": ("Calidad", "Normaliza el formato del codigo de forma automatica."),
    "mypy": ("Calidad", "Verifica los tipos estaticos antes de ejecutar."),
    "python-dotenv": ("Configuracion", "Carga la configuracion sensible desde variables de entorno."),
    "python-jose": ("Autenticacion", "Firma y verifica los tokens JWT de sesion."),
    "passlib": ("Seguridad", "Deriva y verifica hashes de contrasena."),
    "authlib": ("Autenticacion", "Implementa los flujos OAuth/OIDC contra proveedores externos."),
    "boto3": ("Infraestructura", "Habla con los servicios de AWS (almacenamiento, colas, funciones)."),
    "sentry-sdk": ("Observabilidad", "Captura los errores de produccion para su diagnostico."),
    "structlog": ("Observabilidad", "Emite logs estructurados y correlacionables."),
    "streamlit": ("Interfaz", "Genera una interfaz web interactiva directamente desde el script Python."),
    "gradio": ("Interfaz", "Expone una interfaz web para demostrar modelos o funciones."),
    "typer": ("CLI", "Construye la interfaz de linea de comandos a partir de anotaciones de tipo."),
    "click": ("CLI", "Define los comandos y opciones de la interfaz de terminal."),
    "rich": ("CLI", "Da formato legible a la salida en terminal."),
    "scrapy": ("Automatizacion", "Rastrea sitios web y extrae datos de forma masiva."),
}

# ------------------------------------------------------------- otros ecosistemas
_OTHER: dict[str, tuple[str, str]] = {
    "laravel/framework": ("Framework fullstack", "Aporta ORM, enrutado, plantillas y colas en un unico framework PHP."),
    "symfony/framework-bundle": ("Framework fullstack", "Framework PHP modular basado en componentes reutilizables."),
    "github.com/gin-gonic/gin": ("Framework de servidor", "Router HTTP de alto rendimiento para servicios en Go."),
    "github.com/labstack/echo": ("Framework de servidor", "Framework HTTP minimalista para servicios en Go."),
    "actix-web": ("Framework de servidor", "Servidor HTTP de alto rendimiento en Rust."),
    "axum": ("Framework de servidor", "Framework HTTP en Rust construido sobre Tokio."),
    "rails": ("Framework fullstack", "Framework MVC completo con ORM y convenciones sobre configuracion."),
    "sinatra": ("Framework de servidor", "Micro-framework HTTP para Ruby."),
}

KNOWLEDGE: dict[str, tuple[str, str]] = {**_NODE, **_PYTHON, **_OTHER}

# Prefijos de familias enteras: si el paquete empieza asi, hereda el rol.
_FAMILY_PREFIXES: tuple[tuple[str, str, str], ...] = (
    ("@angular/", "Framework UI", "Modulo del framework Angular."),
    ("@nestjs/", "Framework de servidor", "Modulo del framework NestJS."),
    ("@radix-ui/", "Componentes UI", "Primitiva de interfaz accesible y sin estilos."),
    ("@testing-library/", "Testing", "Utilidad para probar la interfaz como lo haria una persona."),
    ("@trpc/", "Capa de API", "Modulo de la capa de procedimientos tipados tRPC."),
    ("@sentry/", "Observabilidad", "Captura los errores de produccion para su diagnostico."),
    ("@aws-sdk/", "Infraestructura", "Cliente de un servicio de AWS."),
    ("@types/", "Lenguaje", "Definiciones de tipos para una libreria sin tipado propio."),
    ("eslint-", "Calidad", "Extension del linter con reglas adicionales."),
    ("django-", "Extension", "Extension del framework Django."),
    ("flask-", "Extension", "Extension del framework Flask."),
)

# Palabras del nombre que sugieren categoria cuando no hay entrada exacta.
_NAME_HINTS: tuple[tuple[str, str, str], ...] = (
    ("eslint", "Calidad", "Participa en el analisis estatico y las convenciones de codigo."),
    ("lint", "Calidad", "Participa en el analisis estatico del codigo."),
    ("jest", "Testing", "Participa en la suite de pruebas unitarias."),
    ("test", "Testing", "Participa en la ejecucion o utilidades de pruebas."),
    ("webpack", "Build", "Participa en el empaquetado de la aplicacion."),
    ("babel", "Build", "Participa en la transpilacion del codigo."),
    ("vite", "Build", "Participa en el servidor de desarrollo y el empaquetado."),
    ("postcss", "Estilos", "Procesa y transforma las hojas de estilo."),
    ("tailwind", "Estilos", "Participa en el sistema de clases utilitarias."),
    ("auth", "Autenticacion", "Participa en la identificacion y sesion del usuario."),
    ("jwt", "Autenticacion", "Participa en la emision o verificacion de tokens de sesion."),
    ("crypt", "Seguridad", "Participa en operaciones criptograficas."),
    ("orm", "ORM", "Participa en el mapeo entre objetos y base de datos."),
    ("sql", "Persistencia", "Participa en el acceso a la base de datos relacional."),
    ("mongo", "Persistencia", "Participa en el acceso a MongoDB."),
    ("redis", "Cache / cola", "Participa en la cache o las colas en memoria."),
    ("logger", "Observabilidad", "Participa en el registro de eventos de la aplicacion."),
    ("i18n", "Internacionalizacion", "Participa en la gestion de traducciones."),
    ("icons", "Componentes UI", "Aporta el conjunto de iconos de la interfaz."),
    ("router", "Enrutado", "Participa en la resolucion de rutas."),
    ("http", "Cliente HTTP", "Participa en la comunicacion HTTP."),
    ("aws", "Infraestructura", "Participa en la integracion con servicios de AWS."),
)


def describe(package: str) -> tuple[str, str] | None:
    """Devuelve (categoria, rol) para un paquete, o None si no se reconoce."""
    name = package.strip().lower()
    if not name:
        return None

    if (exact := KNOWLEDGE.get(name)) is not None:
        return exact

    # "next/font", "github.com/x/y/v2": prueba tambien la raiz del nombre.
    root = "/".join(name.split("/")[:2]) if name.startswith("@") else name.split("/")[0]
    if root != name and (by_root := KNOWLEDGE.get(root)) is not None:
        return by_root

    for prefix, category, role in _FAMILY_PREFIXES:
        if name.startswith(prefix):
            return category, role

    for hint, category, role in _NAME_HINTS:
        if hint in name:
            return category, role

    return None
