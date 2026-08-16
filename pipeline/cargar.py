"""Carga a Supabase por REST, con upsert idempotente.

Se usa PostgREST directo en vez del SDK: el pipeline corre en una Action sin
más dependencias que `requests`, y todo lo que hace falta son cuatro upserts
contra los índices únicos que ya declara el esquema.

La idempotencia no es un detalle: la Action puede reintentarse, y la segunda
corrida del día tiene que ser un no-op, no una fila duplicada. De eso se
encargan `unique (cultivo_id, fecha, nivel, unidad)` y
`unique (producto_retail_id, fecha)` junto con `resolution=merge-duplicates`.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections import defaultdict

import requests

from .catalogo import claves_cultivo, cultivos, ignorados
from .comun import FilaOficial, FilaRetail, sesion
from .config import SUPABASE_SERVICE_KEY, SUPABASE_URL, TIMEOUT
from .normalizar import clave, foto_elegible, precio_por_unidad

log = logging.getLogger("kcuesta.cargar")

LOTE = 500


class Supabase:
    def __init__(self, url: str | None = None, llave: str | None = None):
        self.url = (url or SUPABASE_URL).rstrip("/")
        self.llave = llave or SUPABASE_SERVICE_KEY
        if not self.llave:
            raise RuntimeError(
                "falta SUPABASE_SERVICE_KEY. El pipeline escribe con service_role "
                "a propósito: estas tablas no las toca el navegador."
            )
        self.s = sesion()
        self.s.headers.update({
            "apikey": self.llave,
            "Authorization": f"Bearer {self.llave}",
            "Content-Type": "application/json",
        })

    def _pedir(self, metodo: str, tabla: str, **kw) -> requests.Response:
        resp = self.s.request(metodo, f"{self.url}/rest/v1/{tabla}",
                              timeout=TIMEOUT, **kw)
        if resp.status_code >= 400:
            raise RuntimeError(f"{tabla} {resp.status_code}: {resp.text[:300]}")
        return resp

    def upsert(self, tabla: str, filas: list[dict], en_conflicto: str,
               devolver: bool = False) -> list[dict]:
        if not filas:
            return []
        salida: list[dict] = []
        prefer = "resolution=merge-duplicates,return=" + ("representation" if devolver else "minimal")
        for i in range(0, len(filas), LOTE):
            resp = self._pedir(
                "POST", tabla,
                params={"on_conflict": en_conflicto},
                headers={"Prefer": prefer},
                json=filas[i:i + LOTE],
            )
            if devolver and resp.text:
                salida.extend(resp.json())
        log.info("%s: %d filas cargadas", tabla, len(filas))
        return salida

    def seleccionar(self, tabla: str, **params) -> list[dict]:
        return self._pedir("GET", tabla, params=params).json()


# ------------------------------------------------------------------
# Mapeo de nombre crudo -> cultivo_id
# ------------------------------------------------------------------
class Mapeador:
    """Resuelve nombres de fuente contra el catálogo propio.

    Dos niveles: el nombre del cultivo tal cual (semilla) y la tabla
    `cultivo_alias`, que se llena a mano. Lo que no resuelve NO se adivina —
    se cuenta y se reporta. Un alias equivocado mete un precio ajeno en la
    serie y nadie lo nota; un hueco se ve.
    """

    def __init__(self, db: Supabase | None = None):
        self.mapa: dict[str, str] = dict(claves_cultivo())
        self.ignorados = ignorados()
        self.no_mapeados: dict[str, int] = defaultdict(int)
        if db:
            try:
                for fila in db.seleccionar("cultivo_alias", select="alias,cultivo_id"):
                    self.mapa[fila["alias"]] = fila["cultivo_id"]
            except Exception as e:       # noqa: BLE001
                log.warning("no se pudieron leer los alias: %s", e)
        log.info("mapeador con %d claves", len(self.mapa))

    def resolver(self, nombre_crudo: str) -> str | None:
        k = clave(nombre_crudo)
        if not k or k in self.ignorados:
            return None
        if k in self.mapa:
            return self.mapa[k]
        # Segundo intento: prefijo de dos palabras. 'platano verde barahona'
        # cae en 'platano verde'. Solo prefijo, nunca parecido: recortar por
        # la izquierda conserva el cultivo; el fuzzy lo cambia.
        partes = k.split()
        for n in (3, 2):
            if len(partes) > n:
                corto = " ".join(partes[:n])
                if corto in self.mapa:
                    return self.mapa[corto]
        self.no_mapeados[k] += 1
        return None

    def reporte(self, tope: int = 40) -> str:
        if not self.no_mapeados:
            return "todos los nombres resolvieron a un cultivo"
        orden = sorted(self.no_mapeados.items(), key=lambda x: -x[1])
        lineas = [f"{n:5d}  {k}" for k, n in orden[:tope]]
        extra = len(orden) - tope
        if extra > 0:
            lineas.append(f"       ... y {extra} más")
        return (
            f"{len(orden)} nombres sin mapear ({sum(self.no_mapeados.values())} filas).\n"
            "Añádelos a cultivo_alias:\n" + "\n".join(lineas)
        )


# ------------------------------------------------------------------
# Siembra del catálogo
# ------------------------------------------------------------------
def sembrar_cultivos(db: Supabase) -> int:
    """Empuja data/precios.json a la tabla `cultivos`, que está vacía."""
    from .normalizar import unidades_por_empaque

    filas = []
    for c in cultivos():
        unidad = c.get("unidad_mayorista") or c.get("unidad_minorista") or "Unidad"
        filas.append({
            "id": c["id"],
            "nombre": c["nombre"],
            "calidad": c.get("calidad"),
            "categoria": c["categoria"],
            "unidad_venta": unidad,
            "unidades_por_empaque": unidades_por_empaque(unidad),
            "activo": True,
        })
    db.upsert("cultivos", filas, en_conflicto="id")
    return len(filas)


# ------------------------------------------------------------------
# Serie oficial
# ------------------------------------------------------------------
def cargar_oficiales(db: Supabase, filas: list[FilaOficial], m: Mapeador) -> int:
    """Carga precios_oficiales. Deduplica en memoria antes de enviar.

    El unique de la tabla es (cultivo_id, fecha, nivel, unidad), pero un
    mismo informe trae seis mercados minoristas con la misma unidad para el
    mismo producto. Sin colapsarlos, Postgres rechaza el lote entero por
    'ON CONFLICT DO UPDATE command cannot affect row a second time'. Se
    promedian los mercados del mismo nivel, que es justo lo que el propio
    Ministerio publica como precio minorista.
    """
    cubos: dict[tuple, list[FilaOficial]] = defaultdict(list)
    for f in filas:
        cid = m.resolver(f.nombre_crudo)
        if not cid:
            continue
        cubos[(cid, f.fecha, f.nivel, f.unidad)].append(f)

    salida = []
    for (cid, fecha, nivel, unidad), grupo in cubos.items():
        precio = round(sum(g.precio for g in grupo) / len(grupo), 2)
        ref = grupo[0]
        salida.append({
            "cultivo_id": cid,
            "fecha": fecha.isoformat(),
            "nivel": nivel,
            "unidad": unidad,
            "precio": precio,
            "precio_por_unidad": precio_por_unidad(precio, unidad),
            "fuente": ref.fuente,
            "fuente_url": ref.fuente_url,
        })

    db.upsert("precios_oficiales", salida,
              en_conflicto="cultivo_id,fecha,nivel,unidad")
    return len(salida)


# ------------------------------------------------------------------
# Retail
# ------------------------------------------------------------------
def cargar_retail(db: Supabase, filas: list[FilaRetail], m: Mapeador) -> tuple[int, int]:
    """Carga productos_retail y precios_retail. Devuelve (productos, precios)."""
    if not filas:
        return 0, 0

    unicos: dict[tuple[str, str], FilaRetail] = {}
    for f in filas:
        unicos[(f.cadena_id, f.sku)] = f

    productos = []
    for f in unicos.values():
        productos.append({
            "cadena_id": f.cadena_id,
            "sku_externo": f.sku,
            "nombre_externo": f.nombre,
            "cultivo_id": m.resolver(f.nombre),
            "categoria_externa": f.categoria,
            "unidad_externa": f.unidad,
            "url_producto": f.url_producto,
            "foto_origen_url": f.foto_origen_url,
            "foto_fuente": f.cadena_id,
            # La foto entra en pendiente y no se sirve hasta aprobarse. Lo
            # que ni siquiera es fresco a granel se rechaza de una vez: ahí
            # la imagen es empaque de marca.
            "foto_estado": "pendiente" if foto_elegible(f.categoria or "") else "rechazada",
            "foto_motivo": None if foto_elegible(f.categoria or "") else "categoría no es fresco a granel",
            "visto_ultimo": dt.datetime.now(dt.timezone.utc).isoformat(),
        })

    guardados = db.upsert("productos_retail", productos,
                          en_conflicto="cadena_id,sku_externo", devolver=True)
    ids = {(p["cadena_id"], p["sku_externo"]): p["id"] for p in guardados}

    precios = []
    for f in unicos.values():
        pid = ids.get((f.cadena_id, f.sku))
        if not pid:
            continue
        precios.append({
            "producto_retail_id": pid,
            "fecha": f.fecha.isoformat(),
            "precio": f.precio,
            "precio_lista": f.precio_lista,
            "disponible": f.disponible,
        })

    db.upsert("precios_retail", precios, en_conflicto="producto_retail_id,fecha")
    return len(productos), len(precios)


def registrar_captura(db: Supabase, resultado, no_mapeados: int = 0) -> None:
    """Deja constancia de la corrida, haya ido bien o mal."""
    try:
        db.upsert("capturas", [{
            "fuente": resultado.fuente,
            "fecha": dt.date.today().isoformat(),
            "terminado": dt.datetime.now(dt.timezone.utc).isoformat(),
            "estado": "ok" if resultado.ok and resultado.filas else
                      ("vacio" if resultado.ok else "fallo"),
            "filas": resultado.filas,
            "no_mapeados": no_mapeados,
            "artefacto": resultado.artefacto,
            "error": resultado.error,
        }], en_conflicto="id")
    except Exception as e:               # noqa: BLE001
        log.warning("no se pudo registrar la captura de %s: %s", resultado.fuente, e)
