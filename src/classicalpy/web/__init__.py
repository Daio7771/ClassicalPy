"""Interfaz web y API HTTP. Requiere el extra `web` (fastapi + uvicorn)."""

__all__ = ["app"]


def __getattr__(name: str):
    # Import perezoso: importar classicalpy.web no debe exigir FastAPI si solo
    # se va a usar la CLI.
    if name == "app":
        from classicalpy.web.app import app

        return app
    raise AttributeError(name)
