"""Interfaz de linea de comandos.

    classicalpy analizar ./mi-proyecto
    classicalpy analizar https://github.com/usuario/repo --formato json
    classicalpy servir --puerto 8000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from classicalpy import __version__
from classicalpy.ingest.source import SourceError
from classicalpy.report import FORMATS, render

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USO = 2


def _force_utf8_stdout() -> None:
    """La consola de Windows usa cp1252 y no sabe pintar los emoji del informe.

    Reconfigurarla evita un UnicodeEncodeError que abortaria la ejecucion
    despues de haber hecho todo el trabajo.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="classicalpy",
        description="Analiza un proyecto web y genera un informe de arquitectura.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  classicalpy analizar .\n"
            "  classicalpy analizar ../tienda --salida informe.md\n"
            "  classicalpy analizar https://github.com/pallets/flask --formato json\n"
            "  classicalpy servir\n"
        ),
    )
    parser.add_argument("--version", action="version", version=f"classicalpy {__version__}")
    sub = parser.add_subparsers(dest="comando", required=True)

    analizar = sub.add_parser("analizar", help="Analiza una carpeta local o un repositorio Git.")
    analizar.add_argument("fuente", help="Ruta local o URL del repositorio.")
    analizar.add_argument(
        "--formato", "-f", choices=FORMATS, default="markdown", help="Formato de salida."
    )
    analizar.add_argument(
        "--salida", "-o", type=Path, default=None, help="Fichero donde escribir el informe."
    )
    analizar.add_argument(
        "--max-ficheros", type=int, default=20_000, help="Limite de ficheros a escanear."
    )

    servir = sub.add_parser("servir", help="Levanta la interfaz web y la API.")
    servir.add_argument("--host", default="127.0.0.1", help="Interfaz de red donde escuchar.")
    servir.add_argument("--puerto", "-p", type=int, default=8000, help="Puerto HTTP.")
    servir.add_argument("--recargar", action="store_true", help="Recarga al cambiar el codigo.")

    return parser


def _cmd_analizar(args: argparse.Namespace) -> int:
    from classicalpy.pipeline import run

    try:
        report = run(args.fuente, max_files=args.max_ficheros)
    except SourceError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    salida = render(report, args.formato)

    if args.salida is not None:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(salida, encoding="utf-8")
        print(f"Informe escrito en {args.salida}")
    else:
        print(salida)

    # Un riesgo detectado no es un fallo del analisis: siempre salimos con 0.
    return EXIT_OK


def _cmd_servir(args: argparse.Namespace) -> int:
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print(
            "La interfaz web necesita dependencias extra. Instalalas con:\n"
            "  pip install 'classicalpy[web]'",
            file=sys.stderr,
        )
        return EXIT_ERROR

    import uvicorn

    print(f"ClassicalPy en http://{args.host}:{args.puerto}  (Ctrl+C para parar)")
    uvicorn.run(
        "classicalpy.web.app:app",
        host=args.host,
        port=args.puerto,
        reload=args.recargar,
        log_level="warning",
    )
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    args = build_parser().parse_args(argv)

    try:
        if args.comando == "analizar":
            return _cmd_analizar(args)
        if args.comando == "servir":
            return _cmd_servir(args)
    except KeyboardInterrupt:
        print("\nInterrumpido.", file=sys.stderr)
        return EXIT_ERROR

    return EXIT_USO


if __name__ == "__main__":
    raise SystemExit(main())
