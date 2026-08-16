"""Regenera los JSON estáticos y assets/js/datos.js.

Este archivo cierra un agujero que venía de antes: `assets/js/datos.js` dice
en su cabecera "Generado desde data/*.json" pero el generador nunca estuvo
en el repo, así que los tres archivos se mantenían sincronizados a mano.
Desde aquí, `datos.js` se genera de verdad.

El sitio sigue siendo estático a propósito. La base guarda la serie completa
—que es lo que no se puede perder— y de ahí sale un recorte del día que se
publica como JSON. Ninguna página pide nada a Supabase para pintar precios:
GitHub Pages sirve archivos y ya.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from collections import defaultdict

from .catalogo import cultivos
from .config import ASSETS_JS, DATOS
from .normalizar import sin_tildes

log = logging.getLogger("kcuesta.exportar")

# Banco Creative Commons ya presente en el repo (créditos en
# assets/img/CREDITOS.md). Es el respaldo cuando no hay foto propia
# aprobada, que al principio será casi siempre.
FOTOS_CC = {
    "platano": "platano", "guineo": "guineo", "yuca": "yuca", "batata": "batata",
    "name": "name", "yautia": "yuca", "papa": "batata",
    "aji": "aji", "tomate": "tomate", "berenjena": "berenjena",
    "zanahoria": "zanahoria", "auyama": "zanahoria", "cebolla": "aji",
    "habichuela": "habichuela", "guandul": "habichuela", "arroz": "habichuela",
    "aguacate": "aguacate", "lechosa": "lechosa", "pina": "pina",
    "limon": "pina", "naranja": "pina", "chinola": "pina", "mango": "lechosa",
    "melon": "lechosa", "sandia": "lechosa", "coco": "pina", "zapote": "lechosa",
}


def _foto_cc(cultivo_id: str) -> str:
    base = sin_tildes(cultivo_id).split("-")[0]
    return f"assets/img/{FOTOS_CC.get(base, 'mercado')}.jpg"


def _serie(db, desde: dt.date) -> dict:
    """{(cultivo_id, nivel): [filas ordenadas por fecha desc]}"""
    filas = db.seleccionar(
        "precios_oficiales",
        select="cultivo_id,fecha,nivel,unidad,precio,precio_por_unidad,fuente,fuente_url",
        fecha=f"gte.{desde.isoformat()}",
        order="fecha.desc",
        limit="20000",
    )
    cubos = defaultdict(list)
    for f in filas:
        cubos[(f["cultivo_id"], f["nivel"])].append(f)
    return cubos


def _cambio(serie: list[dict]) -> float | None:
    """Variación porcentual del último dato contra el de hace ~una semana."""
    if len(serie) < 2:
        return None
    ultimo = serie[0]
    fecha_ult = dt.date.fromisoformat(ultimo["fecha"])
    previo = next(
        (f for f in serie[1:]
         if (fecha_ult - dt.date.fromisoformat(f["fecha"])).days >= 5),
        None,
    )
    if not previo or not previo["precio"]:
        return None
    return round((ultimo["precio"] - previo["precio"]) / previo["precio"] * 100, 2)


def _precios(db, hoy: dt.date) -> dict:
    """Arma data/precios.json manteniendo la forma que espera precios.html."""
    with open(DATOS / "precios.json", encoding="utf-8") as f:
        anterior = json.load(f)

    cubos = _serie(db, hoy - dt.timedelta(days=45))
    catalogo = {c["id"]: c for c in cultivos()}
    salida = []
    fuente_ref = None

    for cid, c in catalogo.items():
        may = cubos.get((cid, "mayorista"), [])
        men = cubos.get((cid, "minorista"), [])
        sup = cubos.get((cid, "supermercado"), [])
        col = cubos.get((cid, "colmado"), [])
        if not (may or men):
            continue

        fila = {
            "id": cid,
            "nombre": c["nombre"],
            "categoria": c["categoria"],
        }
        if c.get("calidad"):
            fila["calidad"] = c["calidad"]
        if c.get("destacado"):
            fila["destacado"] = True

        if may:
            u = may[0]
            # La fuente que se cita arriba es el informe del Ministerio, que
            # es el que trae los cinco niveles y el que se puede enlazar como
            # documento. MERCADOM entra como fuente diaria, no como la
            # principal, aunque a veces llegue primero.
            if fuente_ref is None or (
                "Ministerio" in u["fuente"] and "Ministerio" not in fuente_ref["fuente"]
            ):
                fuente_ref = u
            fila["unidad_mayorista"] = u["unidad"]
            fila["precio_mayorista"] = u["precio"]
            fila["precio_mayorista_unidad"] = u["precio_por_unidad"]
            fila["fecha_mayorista"] = u["fecha"]
            cambio = _cambio(may)
            if cambio is not None:
                fila["cambio_semanal_mayorista"] = cambio
        if men:
            u = men[0]
            fila["unidad_minorista"] = u["unidad"]
            fila["precio_minorista"] = u["precio"]
            cambio = _cambio(men)
            if cambio is not None:
                fila["cambio_semanal_minorista"] = cambio
        if sup:
            fila["precio_supermercado"] = sup[0]["precio"]
        if col:
            fila["precio_colmado"] = col[0]["precio"]

        d = fila.get("cambio_semanal_mayorista", 0) or 0
        fila["tendencia"] = "sube" if d > 0.5 else ("baja" if d < -0.5 else "estable")

        # Margen entre lo que recibe el mayorista y lo que paga el minorista,
        # ambos por unidad comparable. Es el número que hace la historia.
        pmu, pm = fila.get("precio_mayorista_unidad"), fila.get("precio_minorista")
        if pmu and pm and pmu > 0:
            fila["margen_mayorista_minorista"] = round((pm - pmu) / pmu * 100, 1)

        salida.append(fila)

    salida.sort(key=lambda x: (x["categoria"], x["nombre"]))

    meta = dict(anterior.get("_meta", {}))
    if fuente_ref:
        meta["fuente_principal"] = {
            **meta.get("fuente_principal", {}),
            "nombre": fuente_ref["fuente"],
            "edicion": fuente_ref["fecha"],
            "url": fuente_ref["fuente_url"],
        }
    meta["actualizado"] = hoy.isoformat()
    meta["generado_por"] = "pipeline/exportar.py"

    return {"_meta": meta, "cultivos": salida,
            "brecha_colmado": anterior.get("brecha_colmado", {})}


def _ofertas(db, hoy: dt.date) -> dict:
    """Ofertas reales de supermercado, para reemplazar las tarjetas de muestra.

    NO se disfrazan de anuncio de productor. Un anuncio de finca tiene corte,
    provincia y un vendedor con teléfono; una oferta de supermercado tiene
    góndola y sucursal. Meter la segunda en la forma de la primera habría
    dado una página más llena y una mentira: el sitio entero se sostiene en
    que cada precio dice de dónde salió.
    """
    productos = db.seleccionar(
        "productos_retail",
        select="id,cadena_id,sku_externo,nombre_externo,cultivo_id,unidad_externa,"
               "url_producto,foto_url,foto_estado,foto_fuente",
        cultivo_id="not.is.null",
        order="id",
        limit="5000",
    )
    if not productos:
        return {"_meta": {}, "ofertas": [], "cadenas": {}}

    por_id = {p["id"]: p for p in productos}
    precios = db.seleccionar(
        "precios_retail",
        select="producto_retail_id,fecha,precio,precio_lista,disponible",
        fecha=f"gte.{(hoy - dt.timedelta(days=7)).isoformat()}",
        order="fecha.desc",
        limit="20000",
    )

    ultimo: dict[int, dict] = {}
    for pr in precios:
        ultimo.setdefault(pr["producto_retail_id"], pr)

    cubos = _serie(db, hoy - dt.timedelta(days=21))
    catalogo = {c["id"]: c for c in cultivos()}

    ofertas = []
    for pid, pr in ultimo.items():
        p = por_id.get(pid)
        if not p or not pr["disponible"]:
            continue
        cid = p["cultivo_id"]
        cult = catalogo.get(cid, {})

        may = cubos.get((cid, "mayorista"), [])
        ref = may[0]["precio_por_unidad"] if may else None

        # Solo se sirve la foto propia si además fue aprobada a ojo.
        propia = p["foto_estado"] == "aprobada" and p["foto_url"]
        ofertas.append({
            "id": f"{p['cadena_id']}-{p['sku_externo']}",
            "cultivo": cid,
            "titulo": p["nombre_externo"],
            "cadena": p["cadena_id"],
            "precio": pr["precio"],
            "precio_lista": pr["precio_lista"],
            "unidad": p["unidad_externa"] or cult.get("unidad_venta") or "Unidad",
            "mercado_ref_unidad": ref,
            "url": p["url_producto"],
            "foto": p["foto_url"] if propia else _foto_cc(cid),
            "foto_propia": bool(propia),
            "foto_credito": p["foto_fuente"] if propia else "Wikimedia Commons (CC)",
            "fecha": pr["fecha"],
        })

    ofertas.sort(key=lambda o: (o["cultivo"], o["precio"]))
    cadenas = {c["id"]: c for c in db.seleccionar(
        "cadenas", select="id,nombre,url,tipo", activo="eq.true")}

    return {
        "_meta": {
            "descripcion": "Precios de góndola capturados de las cadenas dominicanas "
                           "que publican su catálogo. Son precio al consumidor, NO "
                           "precio en finca.",
            "por_que": "Mientras no haya productores publicando, estas ofertas dan "
                       "la referencia contra la cual se leerá la primera oferta de "
                       "finca que entre.",
            "actualizado": hoy.isoformat(),
            "generado_por": "pipeline/exportar.py",
        },
        "ofertas": ofertas,
        "cadenas": cadenas,
    }


def exportar(db, hoy: dt.date | None = None) -> str:
    hoy = hoy or dt.date.today()

    precios = _precios(db, hoy)
    ofertas = _ofertas(db, hoy)

    with open(DATOS / "precios.json", "w", encoding="utf-8") as f:
        json.dump(precios, f, ensure_ascii=False, indent=2)
    with open(DATOS / "ofertas.json", "w", encoding="utf-8") as f:
        json.dump(ofertas, f, ensure_ascii=False, indent=2)

    with open(DATOS / "anuncios.json", encoding="utf-8") as f:
        anuncios = json.load(f)

    # Una sola línea, como estaba: el archivo se sirve tal cual y no hay
    # ninguna razón para gastar bytes en formato.
    compacto = {"separators": (",", ":"), "ensure_ascii": False}
    with open(ASSETS_JS / "datos.js", "w", encoding="utf-8") as f:
        f.write("/* Generado por pipeline/exportar.py — no editar a mano */\n")
        f.write("window.KC={precios:" + json.dumps(precios, **compacto) +
                ",anuncios:" + json.dumps(anuncios, **compacto) +
                ",ofertas:" + json.dumps(ofertas, **compacto) + "};\n")

    propias = sum(1 for o in ofertas["ofertas"] if o["foto_propia"])
    return (f"exportado: {len(precios['cultivos'])} cultivos con precio, "
            f"{len(ofertas['ofertas'])} ofertas de {len(ofertas['cadenas'])} cadenas "
            f"({propias} con foto propia aprobada, el resto con foto CC)")
