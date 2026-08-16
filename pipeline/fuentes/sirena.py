"""La Sirena — VTEX.

VTEX expone su catálogo público sin autenticación en
`/api/catalog_system/pub/products/search`. Devuelve nombre, categoría,
unidad de medida, precio, precio de lista, existencia y la foto — todo lo
que hace falta, en JSON, sin renderizar nada.

Solo se recorren las categorías de fresco. Es lo único que le interesa a
Kcuesta y, de paso, deja fuera el empaquetado de marca, cuya foto es arte
del fabricante y no se espeja.
"""

from __future__ import annotations

import datetime as dt
import logging

from ..comun import FilaRetail, Resultado, sesion
from ..config import TIMEOUT
from ..normalizar import categoria_capturable

log = logging.getLogger("kcuesta.sirena")

BASE = "https://www.sirena.do"
ARBOL = f"{BASE}/api/catalog_system/pub/category/tree/3"
BUSQUEDA = f"{BASE}/api/catalog_system/pub/products/search"
PAGINA = 50          # VTEX rechaza rangos mayores de 50
TOPE_POR_CATEGORIA = 500


def _categorias_capturables(s) -> list[tuple[str, str]]:
    """Devuelve [(fq, ruta)] de las categorías cuyo precio nos sirve.

    VTEX no filtra por el id de la hoja: exige la ruta completa de ids
    desde la raíz, 'C:/1/12/'. Pasarle solo 'C:12' responde 200 con lista
    vacía, que es la peor forma de fallar — parece que la categoría está
    vacía en vez de que el filtro está mal.
    """
    arbol = s.get(ARBOL, timeout=TIMEOUT).json()
    salida: list[tuple[str, str]] = []

    def caminar(nodos, ruta, ids):
        for n in nodos:
            ruta_n = f"{ruta}/{n['name']}" if ruta else n["name"]
            ids_n = ids + [str(n["id"])]
            hijos = n.get("children") or []
            if categoria_capturable(ruta_n):
                salida.append(("C:/" + "/".join(ids_n) + "/", ruta_n))
            if hijos:
                caminar(hijos, ruta_n, ids_n)

    caminar(arbol, "", [])
    # Se quedan las ramas más altas que ya son fresco; sus hijos vienen
    # incluidos en la búsqueda por categoría y repetirlos solo duplica llamadas.
    tope = []
    for cid, ruta in salida:
        if not any(ruta.startswith(otra + "/") for _, otra in salida):
            tope.append((cid, ruta))
    return tope


def capturar(hoy: dt.date | None = None) -> Resultado:
    hoy = hoy or dt.date.today()
    r = Resultado(fuente="sirena")
    vistos: set[str] = set()
    try:
        s = sesion()
        categorias = _categorias_capturables(s)
        log.info("sirena: %d categorías capturables", len(categorias))

        for fq, ruta in categorias:
            desde = 0
            while desde < TOPE_POR_CATEGORIA:
                resp = s.get(
                    BUSQUEDA,
                    params={"fq": fq, "_from": desde, "_to": desde + PAGINA - 1},
                    timeout=TIMEOUT,
                )
                if resp.status_code not in (200, 206):
                    break
                productos = resp.json()
                if not productos:
                    break

                for p in productos:
                    items = p.get("items") or []
                    if not items:
                        continue
                    it = items[0]
                    vendedores = it.get("sellers") or []
                    if not vendedores:
                        continue
                    oferta = vendedores[0].get("commertialOffer", {})
                    sku = str(it.get("itemId") or p.get("productId"))
                    if sku in vistos:
                        continue
                    vistos.add(sku)

                    precio = oferta.get("Price")
                    if not precio or precio <= 0:
                        continue
                    imagenes = it.get("images") or []
                    r.retail.append(FilaRetail(
                        cadena_id="sirena", sku=sku,
                        nombre=p.get("productName", "").strip(),
                        precio=float(precio),
                        precio_lista=float(oferta.get("ListPrice") or 0) or None,
                        fecha=hoy,
                        categoria=(p.get("categories") or [ruta])[0],
                        unidad=it.get("measurementUnit"),
                        disponible=bool(oferta.get("AvailableQuantity", 0)),
                        url_producto=f"{BASE}/{p.get('linkText')}/p" if p.get("linkText") else None,
                        foto_origen_url=imagenes[0]["imageUrl"] if imagenes else None,
                    ))

                desde += PAGINA
                if len(productos) < PAGINA:
                    break

        if not r.retail:
            r.error = "el catálogo respondió pero no se extrajo ningún producto"
        log.info("sirena: %d productos", len(r.retail))
    except Exception as e:               # noqa: BLE001
        r.error = f"{type(e).__name__}: {e}"
        log.error("sirena falló: %s", r.error)
    return r
