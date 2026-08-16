"""Jumbo, Plaza Lama, PriceSmart y AgroExpress — vía Firecrawl.

Las cuatro cadenas sin API abierta:

  Jumbo        403 de Cloudflare a cualquier cliente que no sea navegador
  Plaza Lama   escaparate Instaleap, llaves solo del lado del cliente
  PriceSmart   responde 200 pero el catálogo lo pinta JavaScript
  AgroExpress  WooCommerce con TODAS las rutas REST de producto en 404

Es la pata frágil del pipeline y se trata como tal: corre al final, gasta
créditos, y cuando falla no arrastra a nadie — las seis fuentes anteriores
ya escribieron lo suyo.

AgroExpress merece atención aparte: vende al por mayor directo del campo,
así que es lo más cerca de un precio en finca que se publica en el país.
No es finca —sigue siendo un intermediario con margen— pero es el techo
por debajo del cual debería estar cualquier oferta de productor.
"""

from __future__ import annotations

import datetime as dt
import logging

from ..comun import FilaRetail, Resultado, sesion
from ..config import FIRECRAWL_API_KEY, TIMEOUT
from ..normalizar import categoria_capturable

log = logging.getLogger("kcuesta.firecrawl")

API = "https://api.firecrawl.dev/v2/scrape"

ESQUEMA = {
    "type": "object",
    "properties": {
        "productos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string"},
                    "precio": {"type": "number", "description": "Precio en RD$, solo el número"},
                    "precio_lista": {"type": "number"},
                    "unidad": {"type": "string", "description": "lb, und, kg, saco"},
                    "categoria": {"type": "string"},
                    "url_producto": {"type": "string"},
                    "foto_url": {"type": "string"},
                    "disponible": {"type": "boolean"},
                },
                "required": ["nombre", "precio"],
            },
        }
    },
    "required": ["productos"],
}

INSTRUCCION = (
    "Extrae todos los productos agrícolas frescos del listado: frutas, "
    "vegetales, víveres, tubérculos, carnes y huevos. Ignora productos "
    "empacados de marca, congelados, enlatados, bebidas y limpieza. "
    "El precio va en pesos dominicanos, solo el número."
)

# Páginas de listado por cadena. Se apunta a la góndola de fresco, no a la
# portada: la portada trae promociones rotativas y casi ningún precio.
OBJETIVOS = [
    ("jumbo",       "https://www.jumbo.com.do/frutas-y-vegetales"),
    ("jumbo",       "https://www.jumbo.com.do/carnes-y-pescados"),
    ("plaza-lama",  "https://www.plazalama.com.do/supermercado/frutas-y-vegetales"),
    ("pricesmart",  "https://www.pricesmart.com/es-do/categoria/Alimentos-G10D03/"
                    "Frutas-y-vegetales-G10D04018/G10D04018"),
    ("agroexpress", "https://agroexpressrd.com/distribuidores/vegetales/"),
    ("agroexpress", "https://agroexpressrd.com/"),
]


def _raspar(s, url: str) -> list[dict]:
    resp = s.post(
        API,
        headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                 "Content-Type": "application/json"},
        json={
            "url": url,
            "formats": [{
                "type": "json",
                "schema": ESQUEMA,
                "prompt": INSTRUCCION,
            }],
            "onlyMainContent": True,
            "waitFor": 3000,
        },
        timeout=TIMEOUT * 3,
    )
    resp.raise_for_status()
    cuerpo = resp.json()
    if not cuerpo.get("success"):
        raise RuntimeError(str(cuerpo.get("error"))[:200])
    return ((cuerpo.get("data") or {}).get("json") or {}).get("productos") or []


def capturar(hoy: dt.date | None = None) -> Resultado:
    hoy = hoy or dt.date.today()
    r = Resultado(fuente="firecrawl")
    if not FIRECRAWL_API_KEY:
        r.error = "sin FIRECRAWL_API_KEY; se omiten Jumbo, Plaza Lama, PriceSmart y AgroExpress"
        log.warning(r.error)
        return r

    s = sesion()
    fallos: list[str] = []
    vistos: set[tuple[str, str]] = set()

    for cadena, url in OBJETIVOS:
        try:
            productos = _raspar(s, url)
        except Exception as e:           # noqa: BLE001
            # Una cadena caída no puede tumbar a las otras tres.
            fallos.append(f"{cadena} ({url.split('/')[-1] or 'portada'}): {type(e).__name__}")
            log.warning("firecrawl %s falló: %s", cadena, e)
            continue

        for p in productos:
            nombre = (p.get("nombre") or "").strip()
            precio = p.get("precio")
            if not nombre or not precio or precio <= 0:
                continue
            categoria = p.get("categoria")
            if categoria and not categoria_capturable(categoria):
                continue

            # Sin sku real, el nombre es la identidad estable del producto.
            sku = nombre.lower()[:100]
            if (cadena, sku) in vistos:
                continue
            vistos.add((cadena, sku))

            r.retail.append(FilaRetail(
                cadena_id=cadena, sku=sku, nombre=nombre,
                precio=float(precio),
                precio_lista=float(p["precio_lista"]) if p.get("precio_lista") else None,
                fecha=hoy, categoria=categoria, unidad=p.get("unidad"),
                disponible=p.get("disponible", True),
                url_producto=p.get("url_producto") or url,
                foto_origen_url=p.get("foto_url"),
            ))

    if fallos and not r.retail:
        r.error = "; ".join(fallos)
    elif fallos:
        log.warning("firecrawl parcial, fallaron: %s", "; ".join(fallos))
    log.info("firecrawl: %d productos de %d objetivos", len(r.retail), len(OBJETIVOS))
    return r
