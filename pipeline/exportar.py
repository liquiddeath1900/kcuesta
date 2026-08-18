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
from .config import ASSETS_JS, DATOS, RAIZ
from .normalizar import libras_de_titulo, sin_tildes, unidad_canonica

log = logging.getLogger("kcuesta.exportar")

def resumen_valor(precios_lb: list[float], fuentes: int) -> dict:
    """El valor de referencia de un rubro: la MEDIANA de lo que cobran las
    fuentes, no el mínimo.

    Kcuesta no es un directorio de tiendas — es la foto del mercado. Quien
    llega no viene a saber cuál góndola está más barata hoy; viene a saber a
    cómo está la cosa, que es la pregunta que le da nombre al sitio. Poner
    el mínimo de titular contesta otra pregunta y además premia al más
    barato, que es justo lo que ESCALA.md prohíbe el día que los que
    publiquen sean productores.

    Mediana y no promedio: un saco mal etiquetado o una oferta de liquidación
    arrastran el promedio y no mueven la mediana. Con dos fuentes la mediana
    es el punto medio de las dos, que es lo honesto cuando no hay más.

    p25/p75 salen de aquí para que la banda del rubro sea la MISMA cuenta que
    la banda contra la que se compara un productor. Dos formas distintas de
    medir 'lo normal' en el mismo sitio se contradicen tarde o temprano.
    """
    xs = sorted(x for x in precios_lb if x)
    if not xs:
        return {"valor_lb": None, "p25_lb": None, "p75_lb": None, "n_fuentes": fuentes}

    def cuantil(q: float) -> float:
        # Interpolación lineal, igual que numpy: con 2 y 3 datos el método
        # 'más cercano' salta y la banda se ve escalonada entre rubros.
        if len(xs) == 1:
            return xs[0]
        pos = q * (len(xs) - 1)
        bajo = int(pos)
        alto = min(bajo + 1, len(xs) - 1)
        return round(xs[bajo] + (xs[alto] - xs[bajo]) * (pos - bajo), 2)

    return {
        "valor_lb":  cuantil(0.50),
        "p25_lb":    cuantil(0.25),
        "p75_lb":    cuantil(0.75),
        "n_fuentes": fuentes,
    }



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


def _foto_cc(cultivo_id: str) -> tuple[str, str]:
    """(ruta, crédito) de la foto del rubro, del mejor origen disponible.

    En orden:

    1. `assets/img/rubros/` — la foto de góndola espejada. Es la mejor con
       diferencia: la cadena fotografía el producto limpio sobre blanco,
       que es exactamente lo que la tarjeta necesita.
    2. `assets/img/cultivos/` — Wikimedia Commons por binomio científico.
       Sirve de relleno pero rinde poco: las categorías de Commons están
       curadas para BOTÁNICA, no para comida, así que devuelven la mata, la
       hoja, la corteza y hasta láminas de herbario. En una tanda de 24
       salieron un caldero vacío para el arroz y una hoja enferma para la
       habichuela.
    3. El banco viejo por categoría, que es el que repetía `habichuela.jpg`
       en 47 tarjetas.
    """
    espejada = RAIZ / "assets" / "img" / "rubros" / f"{cultivo_id}.webp"
    if espejada.exists():
        return f"assets/img/rubros/{cultivo_id}.webp", "foto de la cadena"

    propia = RAIZ / "assets" / "img" / "cultivos" / f"{cultivo_id}.webp"
    if propia.exists():
        return f"assets/img/cultivos/{cultivo_id}.webp", "Wikimedia Commons (CC)"

    base = sin_tildes(cultivo_id).split("-")[0]
    return f"assets/img/{FOTOS_CC.get(base, 'mercado')}.jpg", "Wikimedia Commons (CC)"


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
               "url_producto,foto_url,foto_estado,foto_fuente,foto_origen_url,"
               "categoria_externa",
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
        libras = libras_de_titulo(p["nombre_externo"])
        ofertas.append({
            "id": f"{p['cadena_id']}-{p['sku_externo']}",
            "cultivo": cid,
            "titulo": p["nombre_externo"],
            "cadena": p["cadena_id"],
            "precio": pr["precio"],
            "precio_lista": pr["precio_lista"],
            # NO se cae a cult["unidad_venta"]: esa es la unidad MAYORISTA
            # del catálogo —el plátano se cotiza por millar, la yuca por
            # quintal— y aquí estamos en góndola. Cuando la cadena no
            # declaraba unidad, el plátano verde de Nacional salía como
            # "RD$18 / Millar": 18 pesos por mil plátanos. Un SKU de
            # supermercado se vende de uno en uno; el default es Unidad.
            "unidad": unidad_canonica(p["unidad_externa"]),
            "mercado_ref_unidad": ref,
            "url": p["url_producto"],
            "foto": p["foto_url"] if propia else _foto_cc(cid)[0],
            "foto_propia": bool(propia),
            "foto_credito": p["foto_fuente"] if propia else _foto_cc(cid)[1],
            # Se arrastran para que pipeline.fotos_rubro sepa qué bajar y de
            # qué góndola vino, sin volver a consultar la base.
            "foto_origen": p.get("foto_origen_url"),
            "categoria_externa": p.get("categoria_externa"),
            "libras": libras,
            # Precio por libra: la única cifra con la que se pueden comparar
            # una libra suelta y un saco de 50. None cuando el título no dice
            # cuánto trae — se muestra el precio a secas y no se compara.
            "precio_lb": round(pr["precio"] / libras, 2) if libras else None,
            "fecha": pr["fecha"],
        })

    ofertas.sort(key=lambda o: (o["cultivo"], o["precio"]))
    cadenas = {c["id"]: c for c in db.seleccionar(
        "cadenas", select="id,nombre,url,tipo,sede,alcance", activo="eq.true")}

    # Nombre corto para las pastillas de filtro. "Supermercados Nacional"
    # es lo que empujaba la fila fuera de la pantalla; en un chip basta
    # "Nacional". El nombre completo se sigue usando en la tarjeta.
    for c in cadenas.values():
        c["corto"] = (c["nombre"]
                      .replace("Supermercados ", "")
                      .replace("Supermercado ", "")
                      .replace(" Market", "")
                      .replace("La ", "")
                      .replace(" RD", "")
                      .strip())

    # ---- Agrupado por cultivo ----
    # 147 ofertas son apenas 43 rubros: el arroz selecto solo trae 15 y el
    # ají morrón 13. Listadas planas, la página repite "Ají" trece veces
    # seguidas y no se puede escanear. La unidad de la tarjeta pasa a ser el
    # RUBRO, y las cadenas van adentro — que además es la comparación que
    # alguien viene a hacer: no "hay un ají", sino "a cómo está el ají".
    porcultivo: dict[str, list[dict]] = defaultdict(list)
    for o in ofertas:
        porcultivo[o["cultivo"]].append(o)

    rubros = []
    for cid, lista in porcultivo.items():
        cult = catalogo.get(cid, {})

        # Se ordena y se compara POR LIBRA, no por precio de etiqueta. Sin
        # esto la cebolla decía "RD$46 – RD$10,750" porque metía la libra
        # suelta y el saco de 50 en el mismo rango, y el saco salía como si
        # fuera 234 veces más caro cuando por libra es 4.7 veces.
        conlb = [o for o in lista if o["precio_lb"]]
        sinlb = [o for o in lista if not o["precio_lb"]]
        conlb.sort(key=lambda o: o["precio_lb"])
        sinlb.sort(key=lambda o: o["precio"])
        lista = conlb + sinlb           # lo comparable primero

        ref = lista[0]["mercado_ref_unidad"]
        base = conlb or lista
        min_lb = base[0].get("precio_lb")
        max_lb = base[-1].get("precio_lb")

        # El valor de referencia sale solo de lo comparable por libra. Meter
        # el empaque sin peso declarado ensucia la mediana con números que
        # no son del mismo grano.
        valor = resumen_valor([o["precio_lb"] for o in conlb],
                              len({o["cadena"] for o in conlb}))

        # Siete rubros no se venden por peso y nunca se van a poder pesar:
        # el plátano y la piña van por unidad, la leche por litro. Sin esta
        # rama sus tarjetas salen sin titular, como si faltara el dato,
        # cuando el dato está y lo que cambia es la unidad. Solo se agrupan
        # si TODAS las ofertas comparten unidad — mezclar "Unidad" con
        # "Litro" en una mediana no significa nada.
        valor_und = None
        if valor["valor_lb"] is None:
            unidades = {o["unidad"] for o in lista}
            if len(unidades) == 1:
                v = resumen_valor([o["precio"] for o in lista],
                                  len({o["cadena"] for o in lista}))
                valor_und = {"valor_unidad": v["valor_lb"],
                             "unidad_valor": unidades.pop(),
                             "n_fuentes": v["n_fuentes"]}

        rubros.append({
            "cultivo": cid,
            "nombre": cult.get("nombre", cid),
            "categoria": cult.get("categoria"),
            "foto": lista[0]["foto"],
            "foto_credito": lista[0]["foto_credito"],
            "mercado_ref_unidad": ref,
            "n": len(lista),
            "n_comparables": len(conlb),
            "precio_min": base[0]["precio"],
            "precio_max": base[-1]["precio"],
            "precio_lb_min": min_lb,
            "precio_lb_max": max_lb,
            "cadena_min": base[0]["cadena"],
            # Valor de referencia del rubro (mediana) + la banda p25/p75.
            # Es el titular de la tarjeta; min/max quedan como el rango.
            "valor_lb": valor["valor_lb"],
            "p25_lb": valor["p25_lb"],
            "p75_lb": valor["p75_lb"],
            "valor_unidad": (valor_und or {}).get("valor_unidad"),
            "unidad_valor": (valor_und or {}).get("unidad_valor"),
            "n_fuentes": (valor_und or valor)["n_fuentes"],
            # Sobreprecio contra el mayorista, por libra contra libra. Se
            # mide contra la góndola MÁS BARATA a propósito: escoger la más
            # cara inflaría el argumento de la casa.
            # Dos lecturas, a propósito:
            #   sobreprecio      — el VALOR de referencia contra el mayorista.
            #                      Es lo que la tarjeta enseña, porque el
            #                      titular ya es el valor y mezclar bases
            #                      haría que el % no cuadre con la cifra.
            #   sobreprecio_min  — la góndola más barata contra el mayorista.
            #                      Conservador; es el que usa la portada,
            #                      donde el número es un argumento y conviene
            #                      que sea el piso y no el centro.
            "sobreprecio": (round((valor["valor_lb"] - ref) / ref * 100)
                            if ref and valor["valor_lb"] else None),
            "sobreprecio_min": (round((min_lb - ref) / ref * 100)
                                if ref and min_lb else None),
            "ofertas": [{
                "cadena": o["cadena"], "titulo": o["titulo"], "precio": o["precio"],
                "precio_lista": o["precio_lista"], "unidad": o["unidad"],
                "precio_lb": o["precio_lb"], "libras": o["libras"],
                "url": o["url"], "fecha": o["fecha"],
                # Solo los usa pipeline.fotos_rubro para decidir qué espejar.
                "foto_origen": o["foto_origen"],
                "categoria_externa": o["categoria_externa"],
            } for o in lista],
        })

    # Orden por defecto: cuántas cadenas lo cargan, de mayor a menor. Es el
    # mejor sustituto de "popularidad" que hay sin analítica — si diez
    # cadenas venden arroz y una vende zapote, es porque el arroz es lo que
    # la gente compra.
    #
    # La tentación era ordenar por sobreprecio, que es el argumento de la
    # casa. Pero eso pone de primero los rubros exóticos con márgenes raros
    # y esconde el plátano y el arroz, que es lo que alguien vino a buscar.
    # El sobreprecio queda como opción de orden, no como default.
    rubros.sort(key=lambda r: (-r["n"], r["nombre"]))

    # ---- Agrupado por vendedor ----
    # El mismo problema en el otro eje. Agrupar solo por rubro esconde que
    # una cadena aparece en cuarenta tarjetas; y cuando entren productores
    # de verdad, una finca va a publicar plátano, yuca y ají a la vez. Son
    # dos preguntas distintas y las dos son legítimas:
    #     "¿a cómo está el ají?"        -> por rubro
    #     "¿qué tiene esta finca?"      -> por vendedor
    # Se exportan los dos ejes sobre los mismos datos y la página alterna.
    porvendedor: dict[str, list[dict]] = defaultdict(list)
    for o in ofertas:
        porvendedor[o["cadena"]].append(o)

    vendedores = []
    for vid, lista in porvendedor.items():
        cad = cadenas.get(vid, {})
        lista.sort(key=lambda o: (o["cultivo"], o["precio"]))
        conref = [o for o in lista if o["mercado_ref_unidad"]]
        sobre = [round((o["precio"] - o["mercado_ref_unidad"]) / o["mercado_ref_unidad"] * 100)
                 for o in conref]
        rubros_vend = sorted({o["cultivo"] for o in lista})

        vendedores.append({
            "id": vid,
            "nombre": cad.get("nombre", vid),
            "tipo": cad.get("tipo", "supermercado"),
            "url": cad.get("url"),
            "n": len(lista),
            "n_rubros": len(rubros_vend),
            "rubros": rubros_vend,
            # La mediana, no el promedio: un solo rubro con 400% de
            # sobreprecio arrastraría el promedio y daría una lectura falsa
            # de toda la cadena.
            "sobreprecio_mediana": (sorted(sobre)[len(sobre) // 2] if sobre else None),
            "articulos": [{
                "cultivo": o["cultivo"],
                "nombre": catalogo.get(o["cultivo"], {}).get("nombre", o["cultivo"]),
                "titulo": o["titulo"], "precio": o["precio"], "unidad": o["unidad"],
                "mercado_ref_unidad": o["mercado_ref_unidad"],
                "foto": o["foto"], "url": o["url"],
            } for o in lista],
        })

    vendedores.sort(key=lambda v: -v["n"])

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
        "rubros": rubros,
        "vendedores": vendedores,
        "cadenas": cadenas,
    }


def _portada(ofertas: dict, hoy: dt.date) -> dict:
    """Tres rubros para la muestra de la portada.

    Se escogen por sobreprecio, que es lo que la portada tiene que contar,
    pero solo entre los que traen VARIAS tiendas: un rubro con una sola
    oferta da un porcentaje llamativo y ninguna comparación que enseñar, que
    es justo lo que la portada promete.

    Usa el MISMO valor de referencia y el MISMO sobreprecio que el mercado.
    Se probó dejar aquí el conservador —la góndola más barata contra el
    mayorista, que como argumento es más difícil de discutir— y no sirve:
    el mismo rubro salía con un porcentaje en la portada y otro adentro, y
    eso no se lee como prudencia, se lee como un bug. Una sola definición
    en todo el sitio vale más que un par de puntos de margen.

    `sobreprecio_min` se sigue exportando en ofertas.json por si hace falta
    la lectura conservadora, pero no se pinta en ninguna parte.
    """
    candidatos = [r for r in ofertas["rubros"]
                  if r.get("sobreprecio") is not None and r["n"] >= 3]
    candidatos.sort(key=lambda r: -r["sobreprecio"])

    return {
        "_meta": {
            "actualizado": hoy.isoformat(),
            "nota": "Recorte de ofertas.json para la portada. Generado por pipeline/exportar.py",
        },
        "total": len(ofertas["rubros"]),
        "cadenas": ofertas["cadenas"],
        "rubros": [{
            "cultivo": r["cultivo"], "nombre": r["nombre"], "foto": r["foto"],
            "n": r["n"], "precio_lb_min": r["precio_lb_min"],
            "precio_lb_max": r["precio_lb_max"],
            "mercado_ref_unidad": r["mercado_ref_unidad"],
            "sobreprecio": r["sobreprecio"],
            "valor_lb": r["valor_lb"],
            "n_fuentes": r["n_fuentes"],
            "cadena_min": r["cadena_min"],
        } for r in candidatos[:3]],
    }


def exportar(db, hoy: dt.date | None = None) -> str:
    hoy = hoy or dt.date.today()

    precios = _precios(db, hoy)
    ofertas = _ofertas(db, hoy)

    with open(DATOS / "precios.json", "w", encoding="utf-8") as f:
        json.dump(precios, f, ensure_ascii=False, indent=2)
    with open(DATOS / "ofertas.json", "w", encoding="utf-8") as f:
        json.dump(ofertas, f, ensure_ascii=False, indent=2)

    # Recorte para la portada. La portada NO carga datos.js: son 149 KB para
    # enseñar tres tarjetas, y a 384 Kbps eso son tres segundos antes de que
    # aparezca nada. Con este archivo de ~2 KB la muestra es real y sigue
    # siendo real mañana, sin pegarle el mercado entero a quien solo pasaba
    # a ver qué es esto.
    with open(DATOS / "portada.json", "w", encoding="utf-8") as f:
        json.dump(_portada(ofertas, hoy), f, ensure_ascii=False, indent=2)

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
