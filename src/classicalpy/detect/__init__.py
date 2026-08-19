"""Capa de deteccion: de ficheros crudos a stack, dependencias y arquitectura."""

from classicalpy.detect.knowledge import describe
from classicalpy.detect.manifests import collect_manifests
from classicalpy.detect.stack import Signals, build_signals, build_stack, infer_architecture

__all__ = [
    "describe",
    "collect_manifests",
    "Signals",
    "build_signals",
    "build_stack",
    "infer_architecture",
]
