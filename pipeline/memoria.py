"""Base en memoria: el mismo contrato que `Supabase`, sin red.

Sirve para dos cosas, y la segunda importa más que la primera:

  1. Probar el pipeline completo —captura, mapeo, exportación— sin llave de
     servicio ni migraciones aplicadas.
  2. Ser la salida de emergencia. Si Supabase está caído o pausado el día
     que toca capturar, `--sin-base` igual descarga MERCADOM, lo archiva en
     disco y regenera el sitio. La serie histórica se resiente; el archivo
     crudo del día, que es lo irrecuperable, no.

Implementa solo el subconjunto de PostgREST que usa `exportar.py`: `eq.`,
`gte.`, `not.is.null`, `is.null`, `order` y `limit`. No pretende ser un
PostgREST — pretende no mentirle a `exportar.py`.
"""

from __future__ import annotations

import datetime as dt
import itertools
import logging

from .cargar import Mapeador
from .comun import FilaOficial, FilaRetail
from .normalizar import foto_elegible, precio_por_unidad

log = logging.getLogger("kcuesta.memoria")


class BaseEnMemoria:
    def __init__(self):
        self.tablas: dict[str, list[dict]] = {
            "precios_oficiales": [],
            "productos_retail": [],
            "precios_retail": [],
            "cadenas": [],
            "cultivos": [],
            "capturas": [],
        }
        self._siguiente_id = itertools.count(1)

    # -------------------- escritura --------------------
    def upsert(self, tabla: str, filas: list[dict], en_conflicto: str,
               devolver: bool = False) -> list[dict]:
        claves = [c.strip() for c in en_conflicto.split(",")]
        destino = self.tablas.setdefault(tabla, [])
        indice = {tuple(f.get(k) for k in claves): f for f in destino}

        for fila in filas:
            k = tuple(fila.get(c) for c in claves)
            if k in indice:
                indice[k].update(fila)
            else:
                nueva = dict(fila)
                nueva.setdefault("id", next(self._siguiente_id))
                destino.append(nueva)
                indice[k] = nueva
        return destino if devolver else []

    # -------------------- lectura --------------------
    def seleccionar(self, tabla: str, **params) -> list[dict]:
        filas = list(self.tablas.get(tabla, []))

        for campo, expr in params.items():
            if campo in {"select", "order", "limit"}:
                continue
            filas = [f for f in filas if self._pasa(f.get(campo), str(expr))]

        if orden := params.get("order"):
            campo, _, direccion = orden.partition(".")
            filas.sort(key=lambda f: (f.get(campo) is None, f.get(campo)),
                       reverse=direccion == "desc")
        if tope := params.get("limit"):
            filas = filas[:int(tope)]
        return filas

    @staticmethod
    def _pasa(valor, expr: str) -> bool:
        if expr == "not.is.null":
            return valor is not None
        if expr == "is.null":
            return valor is None
        operador, _, esperado = expr.partition(".")
        if operador == "eq":
            return str(valor) == esperado or valor is (esperado == "true")
        if operador == "gte":
            return valor is not None and str(valor) >= esperado
        if operador == "lte":
            return valor is not None and str(valor) <= esperado
        return True


def poblar(base: BaseEnMemoria, oficiales: list[FilaOficial],
           retail: list[FilaRetail], m: Mapeador) -> tuple[int, int]:
    """Mete lo capturado en la base en memoria con las mismas reglas que `cargar`."""
    from collections import defaultdict

    from .cargar import cargar_oficiales, cargar_retail
    from .catalogo import cultivos

    base.upsert("cadenas", [
        {"id": "sirena", "nombre": "La Sirena", "url": "https://www.sirena.do", "tipo": "supermercado", "activo": True},
        {"id": "nacional", "nombre": "Supermercados Nacional", "url": "https://supermercadosnacional.com", "tipo": "supermercado", "activo": True},
        {"id": "fruttissimo", "nombre": "Fruttissimo Market", "url": "https://fruttissimodr.com", "tipo": "supermercado", "activo": True},
        {"id": "jumbo", "nombre": "Jumbo", "url": "https://www.jumbo.com.do", "tipo": "supermercado", "activo": True},
        {"id": "plaza-lama", "nombre": "Plaza Lama", "url": "https://www.plazalama.com.do", "tipo": "supermercado", "activo": True},
        {"id": "pricesmart", "nombre": "PriceSmart", "url": "https://www.pricesmart.com/es-do", "tipo": "supermercado", "activo": True},
        {"id": "agroexpress", "nombre": "AgroExpress RD", "url": "https://agroexpressrd.com", "tipo": "mayorista_online", "activo": True},
    ], en_conflicto="id")

    n_of = cargar_oficiales(base, oficiales, m)
    n_pr, _ = cargar_retail(base, retail, m)
    return n_of, n_pr
