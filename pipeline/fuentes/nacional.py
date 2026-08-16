"""Supermercados Nacional — Magento 2, GraphQL público.

El endpoint `/graphql` responde sin autenticación y devuelve nombre, sku,
precio final en DOP y la imagen.

Se captura por BÚSQUEDA, no por categoría. Su `categoryList` devuelve 110
categorías planas —'Frutas Cítricas', 'Queso Manchego'— y no incluye ni
vegetales ni víveres, así que recorrer el árbol deja fuera justo lo que
Kcuesta necesita. En cambio `products(search:)` sí los encuentra: 'platano'
devuelve 299 referencias. Se interroga con los nombres de los cultivos del
catálogo propio, que además acota la captura a lo agropecuario.
"""

from __future__ import annotations

import datetime as dt
import logging

from ..catalogo import terminos_busqueda
from ..comun import FilaRetail, Resultado, sesion
from ..config import TIMEOUT
from ..normalizar import categoria_capturable

log = logging.getLogger("kcuesta.nacional")

BASE = "https://supermercadosnacional.com"
GRAPHQL = f"{BASE}/graphql"
PAGINA = 100
# Tres páginas por término bastan: la búsqueda más ancha ('platano') devuelve
# 299 referencias. Subirlo solo agrega minutos de cola en la Action.
TOPE_PAGINAS = 3
HILOS = 6

Q_PRODUCTOS = """
query ($texto: String!, $pagina: Int!, $tam: Int!) {
  products(search: $texto, pageSize: $tam, currentPage: $pagina) {
    total_count
    items {
      name sku url_key
      small_image { url }
      stock_status
      categories { name }
      price_range { minimum_price {
        final_price { value currency }
        regular_price { value }
      } }
    }
  }
}
"""


def _consultar(s, query: str, variables: dict | None = None) -> dict:
    resp = s.post(
        GRAPHQL,
        json={"query": query, "variables": variables or {}},
        headers={"Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    datos = resp.json()
    if "errors" in datos:
        raise RuntimeError(str(datos["errors"])[:200])
    return datos["data"]


def capturar(hoy: dt.date | None = None) -> Resultado:
    hoy = hoy or dt.date.today()
    r = Resultado(fuente="nacional")
    vistos: set[str] = set()
    try:
        from concurrent.futures import ThreadPoolExecutor

        s = sesion()
        terminos = terminos_busqueda()
        log.info("nacional: %d términos de búsqueda", len(terminos))

        def buscar(texto: str) -> list[dict]:
            items: list[dict] = []
            for pagina in range(1, TOPE_PAGINAS + 1):
                try:
                    datos = _consultar(s, Q_PRODUCTOS,
                                       {"texto": texto, "pagina": pagina, "tam": PAGINA})
                except Exception as e:   # noqa: BLE001
                    log.warning("nacional '%s' p%d: %s", texto, pagina, e)
                    break
                lote = datos["products"]["items"]
                items.extend(lote)
                if len(lote) < PAGINA:
                    break
            return items

        with ThreadPoolExecutor(max_workers=HILOS) as pool:
            for items in pool.map(buscar, terminos):
                for p in items:
                    sku = str(p.get("sku") or "")
                    if not sku or sku in vistos:
                        continue
                    minimo = (p.get("price_range") or {}).get("minimum_price") or {}
                    precio = (minimo.get("final_price") or {}).get("value")
                    if not precio or precio <= 0:
                        continue

                    categoria = " / ".join(
                        c["name"] for c in (p.get("categories") or []) if c.get("name")
                    )
                    # La búsqueda de Magento es generosa: 'coco' trae galletas
                    # y desodorante. El filtro de categoría es lo que evita
                    # que eso entre a una base de precios agrícolas.
                    if categoria and not categoria_capturable(categoria):
                        continue

                    vistos.add(sku)
                    regular = (minimo.get("regular_price") or {}).get("value")
                    r.retail.append(FilaRetail(
                        cadena_id="nacional", sku=sku,
                        nombre=(p.get("name") or "").strip(),
                        precio=float(precio),
                        precio_lista=float(regular) if regular else None,
                        fecha=hoy, categoria=categoria or None,
                        disponible=(p.get("stock_status") == "IN_STOCK"),
                        url_producto=f"{BASE}/{p['url_key']}.html" if p.get("url_key") else None,
                        foto_origen_url=(p.get("small_image") or {}).get("url"),
                    ))

        if not r.retail:
            r.error = "GraphQL respondió pero no se extrajo ningún producto"
        log.info("nacional: %d productos", len(r.retail))
    except Exception as e:               # noqa: BLE001
        r.error = f"{type(e).__name__}: {e}"
        log.error("nacional falló: %s", r.error)
    return r
