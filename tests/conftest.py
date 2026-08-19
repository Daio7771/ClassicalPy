"""Utilidades compartidas: construccion de proyectos falsos en disco.

Probar un analizador exige tener proyectos que analizar. En vez de fijar
repositorios reales (lentos y cambiantes), fabricamos arboles minimos que
contienen justo las senales que cada test quiere comprobar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def escribir(raiz: Path, ficheros: dict[str, str]) -> Path:
    """Crea un arbol de ficheros a partir de {ruta relativa: contenido}."""
    for ruta, contenido in ficheros.items():
        destino = raiz / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
    return raiz


@pytest.fixture
def crear_proyecto(tmp_path: Path):
    """Devuelve una funcion que materializa un proyecto en un directorio temporal."""

    contador = {"n": 0}

    def _crear(ficheros: dict[str, str], nombre: str | None = None) -> Path:
        contador["n"] += 1
        raiz = tmp_path / (nombre or f"proyecto{contador['n']}")
        raiz.mkdir(parents=True, exist_ok=True)
        return escribir(raiz, ficheros)

    return _crear


@pytest.fixture
def proyecto_next(crear_proyecto):
    """Aplicacion Next.js con Prisma, autenticacion y tests: caso 'fullstack SSR'."""
    package = {
        "name": "tienda-web",
        "version": "1.2.0",
        "description": "Tienda en linea con catalogo y carrito.",
        "scripts": {"dev": "next dev", "build": "next build", "test": "vitest"},
        "dependencies": {
            "next": "14.1.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "@prisma/client": "^5.9.0",
            "next-auth": "^4.24.0",
            "zod": "^3.22.0",
            "tailwindcss": "^3.4.0",
        },
        "devDependencies": {"typescript": "^5.3.0", "vitest": "^1.2.0", "eslint": "^8.56.0"},
    }
    return crear_proyecto(
        {
            "package.json": json.dumps(package, indent=2),
            "package-lock.json": '{"lockfileVersion": 3}',
            "README.md": "# Tienda Web\n\nPlataforma de comercio electronico para vender ropa.\n",
            ".env.example": "DATABASE_URL=\n",
            "app/page.tsx": "export default function Home() { return null }\n" * 12,
            "app/checkout/page.tsx": "export default function Checkout() { return null }\n" * 20,
            "app/api/orders/route.ts": "export async function POST() {}\n" * 15,
            "components/ProductCard.tsx": "export const ProductCard = () => null\n" * 10,
            "components/CartSummary.tsx": "export const CartSummary = () => null\n" * 10,
            "lib/db.ts": "export const db = null\n" * 5,
            "services/orderService.ts": "export async function createOrder() {}\n" * 30,
            "prisma/schema.prisma": "model Order { id Int @id }\n" * 8,
            "tests/checkout.test.ts": "test('checkout', () => {})\n" * 6,
            "tests/orders.test.ts": "test('orders', () => {})\n" * 6,
            ".github/workflows/ci.yml": "name: CI\non: push\n",
        },
        nombre="tienda-web",
    )


@pytest.fixture
def proyecto_fastapi(crear_proyecto):
    """API en FastAPI sin interfaz: caso 'servicio de API'."""
    return crear_proyecto(
        {
            "pyproject.toml": (
                "[project]\n"
                'name = "facturacion-api"\n'
                'version = "0.3.0"\n'
                'description = "API de facturacion para pymes."\n'
                'dependencies = ["fastapi>=0.110", "sqlalchemy>=2.0", "psycopg[binary]>=3.1"]\n'
            ),
            "src/main.py": "from fastapi import FastAPI\napp = FastAPI()\n" * 4,
            "src/models/invoice.py": "class Invoice: pass\n" * 20,
            "src/services/billing.py": "def emitir_factura(): ...\n" * 25,
            "src/schemas/invoice.py": "class InvoiceIn: pass\n" * 10,
        },
        nombre="facturacion-api",
    )


@pytest.fixture
def proyecto_vacio(crear_proyecto):
    """Carpeta sin nada analizable: comprueba la degradacion elegante."""
    return crear_proyecto({"notas.bin": "\x00\x01"}, nombre="vacio")
