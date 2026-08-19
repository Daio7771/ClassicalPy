"""Permite `python -m classicalpy` sin instalar el paquete."""

from classicalpy.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
