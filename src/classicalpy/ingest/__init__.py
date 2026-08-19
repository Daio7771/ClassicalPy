"""Capa de ingesta: obtiene el codigo y lo convierte en un inventario de ficheros."""

from classicalpy.ingest.scanner import Scanner
from classicalpy.ingest.source import ResolvedSource, resolve_source

__all__ = ["Scanner", "ResolvedSource", "resolve_source"]
