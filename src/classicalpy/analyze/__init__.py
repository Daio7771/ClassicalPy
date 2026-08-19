"""Capa de analisis: convierte las senales detectadas en las secciones del informe."""

from classicalpy.analyze.diagnostics import diagnose
from classicalpy.analyze.domain import build_pitch, infer_domain
from classicalpy.analyze.flow import build_flow
from classicalpy.analyze.modules import build_modules

__all__ = ["diagnose", "infer_domain", "build_pitch", "build_flow", "build_modules"]
