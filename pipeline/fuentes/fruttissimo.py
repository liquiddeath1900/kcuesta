"""Fruttissimo Market — WooCommerce Store API.

`/wp-json/wc/store/v1/products` es público y sin llave. Paginable y con
foto. Es la cadena más pequeña de las tres con API abierta, pero es la más
enfocada: vende fruta y vegetal fresco casi en exclusiva, así que la razón
señal/ruido es la mejor del grupo.

Detalle que muerde: la Store API devuelve el precio en unidades MENORES.
`"price": "13000"` con `"currency_minor_unit": 2` son RD$130.00, no
RD$13,000. Tomarlo literal mete un error de cien veces en la serie.
"""

from __future__ import annotations

import datetime as dt
import logging

from ..comun import FilaRetail, Resultado, sesion
from ..config import TIMEOUT
from ..normalizar import categoria_capturable

log = logging.getLogger("kcuesta.fruttissimo")

BASE = "https://fruttissimodr.com"
PRODUCTOS = f"{BASE}/wp-json/wc/store/v1/products"
PAGINA = 100
TOPE_PAGINAS = 20


def _a_pesos(valor, minor_unit) -> float | None:
    if valor in (None, ""):
        return None
    try:
        return round(float(valor) / (10 ** int(minor_unit or 0)), 2)
    except (TypeError, ValueError):
        return None


def capturar(hoy: dt.date | None = None) -> Resultado:
    hoy = hoy or dt.date.today()
    r = Resultado(fuente="fruttissimo")
    try:
        s = sesion()
        for pagina in range(1, TOPE_PAGINAS + 1):
            resp = s.get(PRODUCTOS, params={"per_page": PAGINA, "page": pagina},
                         timeout=TIMEOUT)
            if resp.status_code != 200:
                break
            productos = resp.json()
            if not isinstance(productos, list) or not productos:
                break

            for p in productos:
                categoria = " / ".join(
                    c["name"] for c in (p.get("categories") or []) if c.get("name")
                )
                if categoria and not categoria_capturable(categoria):
                    continue

                precios = p.get("prices") or {}
                minor = precios.get("currency_minor_unit", 2)
                precio = _a_pesos(precios.get("price"), minor)
                if not precio or precio <= 0:
                    continue

                imagenes = p.get("images") or []
                r.retail.append(FilaRetail(
                    cadena_id="fruttissimo", sku=str(p.get("id")),
                    nombre=(p.get("name") or "").strip(),
                    precio=precio,
                    precio_lista=_a_pesos(precios.get("regular_price"), minor),
                    fecha=hoy, categoria=categoria or None,
                    disponible=p.get("is_in_stock", True),
                    url_producto=p.get("permalink"),
                    foto_origen_url=imagenes[0].get("src") if imagenes else None,
                ))

            if len(productos) < PAGINA:
                break

        if not r.retail:
            r.error = "la Store API respondió pero no se extrajo ningún producto"
        log.info("fruttissimo: %d productos", len(r.retail))
    except Exception as e:               # noqa: BLE001
        r.error = f"{type(e).__name__}: {e}"
        log.error("fruttissimo falló: %s", r.error)
    return r
