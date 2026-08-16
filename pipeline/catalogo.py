"""Catálogo de cultivos de Kcuesta y términos de búsqueda derivados.

Fuente de verdad: `data/precios.json`, que es lo que hoy alimenta el sitio.
Cuando la tabla `cultivos` de Supabase esté poblada, `cargar.py` la siembra
desde aquí, así que este archivo sigue siendo el origen.
"""

from __future__ import annotations

import json
from functools import lru_cache

from .config import DATOS
from .normalizar import clave, sin_tildes

# Cadenas cuyo catálogo es enorme y cuya taxonomía no sirve para filtrar.
# Ahí no se recorre por categoría: se busca por el nombre de cada cultivo
# que a Kcuesta le importa. Es menos elegante y bastante más robusto — no
# depende de cómo la cadena decida reorganizar su árbol el mes que viene.
EXTRA_BUSQUEDA = [
    "platano", "guineo", "yuca", "batata", "name", "yautia", "papa",
    "aji", "tomate", "cebolla", "zanahoria", "berenjena", "auyama",
    "lechuga", "repollo", "pepino", "molondron", "habichuela", "guandul",
    "arroz", "aguacate", "lechosa", "pina", "chinola", "limon", "naranja",
    "coco", "melon", "mango", "huevos", "leche", "pollo", "cerdo", "res",
]


@lru_cache(maxsize=1)
def cultivos() -> list[dict]:
    """Catálogo completo: el que muestra el sitio más la extensión oficial.

    `precios.json` trae los 28 cultivos que hoy se publican en precios.html.
    Las fuentes oficiales reportan 123 nombres distintos, así que
    `cultivos_extra.json` cubre el resto: sin una fila en `cultivos` no se
    puede guardar el precio, porque `precios_oficiales.cultivo_id` es NOT NULL.
    """
    with open(DATOS / "precios.json", encoding="utf-8") as f:
        base = json.load(f)["cultivos"]
    with open(DATOS / "cultivos_extra.json", encoding="utf-8") as f:
        extra = json.load(f)["cultivos"]

    vistos = {c["id"] for c in base}
    return base + [c for c in extra if c["id"] not in vistos]


@lru_cache(maxsize=1)
def alias() -> dict[str, str]:
    """{clave normalizada -> cultivo_id}, escrito a mano en data/alias.json."""
    with open(DATOS / "alias.json", encoding="utf-8") as f:
        return json.load(f)["alias"]


@lru_cache(maxsize=1)
def ignorados() -> set[str]:
    """Nombres oficiales que no son producto de finca. No son un pendiente."""
    with open(DATOS / "alias.json", encoding="utf-8") as f:
        datos = json.load(f).get("ignorados", {})
    return {k for k in datos if not k.startswith("_")}


@lru_cache(maxsize=1)
def terminos_busqueda() -> list[str]:
    """Palabras con las que se interroga a las cadenas que no se pueden recorrer.

    Se usa la primera palabra del nombre del cultivo, no el nombre completo:
    buscar 'Plátano barahonero' en un supermercado no devuelve nada porque
    ahí el plátano no se vende por variedad de finca; buscar 'platano' trae
    las 299 referencias que sí existen.
    """
    palabras = {sin_tildes(c["nombre"]).lower().split()[0] for c in cultivos()}
    palabras.update(EXTRA_BUSQUEDA)
    return sorted(p for p in palabras if len(p) > 2)


@lru_cache(maxsize=1)
def claves_cultivo() -> dict[str, str]:
    """{clave normalizada -> cultivo_id}: catálogo propio + alias a mano.

    Los alias van después para que puedan corregir una coincidencia por
    nombre. La tabla `cultivo_alias` de Supabase se apila encima de esto en
    tiempo de ejecución, así que se puede arreglar un mapeo desde la base
    sin tocar el repo.
    """
    mapa = {clave(c["nombre"]): c["id"] for c in cultivos()}
    mapa.update(alias())
    return mapa
