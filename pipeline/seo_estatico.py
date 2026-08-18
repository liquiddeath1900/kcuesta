#!/usr/bin/env python3
"""
Rellenar el HTML con los precios que hoy solo existen en JavaScript.

EL PROBLEMA
    gremio.html pesa 1.4 KB de texto cuando lo pide un robot y ~14 KB
    cuando lo pinta un navegador. Todo el parte del Mercado Nuevo -que es
    el unico dato que nadie mas publica- vive dentro de un fetch. Google
    ejecuta JavaScript, pero lo hace en una segunda pasada que para un
    dominio nuevo y sin enlaces puede tardar dias; y el precio del platano
    de hoy no le sirve a nadie dentro de tres dias. Los demas robots
    -Bing, y los rastreadores de los asistentes, por donde cada vez mas
    gente pregunta "a como esta el aguacate"- no ejecutan nada.

LA SOLUCION, Y POR QUE ESTA Y NO OTRA
    NO se reimplementa el render. gremio.js son 573 lineas de reglas que
    costaron caro -la escalera de calidad, el arrastre por renglon, no
    comparar grados distintos- y copiarlas a Python garantiza que un dia
    las dos versiones digan numeros distintos.

    En vez de eso se escribe una TABLA SIMPLE dentro del mismo contenedor
    que el JavaScript sobreescribe (#rejilla, #tbody). Sin JavaScript se
    ve la tabla; con JavaScript, el fetch la reemplaza por las tarjetas.
    No es un truco para el robot: es exactamente lo mismo que ve el
    visitante, y en una conexion lenta le llega ANTES que el JSON.

    Cada numero sale con su unidad, su fuente y su fecha, como en todo el
    resto del sitio. Si el dato no trae unidad, la celda lo dice; no se
    inventa.

USO
    python3 pipeline/seo_estatico.py          # reescribe el HTML y el sitemap
    Correr despues de cada parte nuevo y despues del pipeline de precios.
"""
import json, os, re, datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://kcuesta.com/"
MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto",
         "septiembre","octubre","noviembre","diciembre"]


def leer(rel):
    with open(os.path.join(RAIZ, rel), encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    return (str("" if s is None else s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def fecha_larga(iso):
    a, m, d = str(iso).split("-")
    return "%d de %s %s" % (int(d), MESES[int(m) - 1], a)


def rd(n, dec=2):
    if n is None:
        return "—"
    return "RD$ " + ("{:,.%df}" % dec).format(float(n))



def num_es(n, dec=2):
    return ("{:,.%df}" % dec).format(float(n))

def rango(a, b, dec=0):
    if a == b:
        return rd(a, dec)
    return "%s – %s" % (rd(a, dec), ("{:,.%df}" % dec).format(float(b)))


def entre_marcas(html, marca, dentro):
    """Reemplaza lo que haya entre <!--marca--> y <!--/marca-->.

    Si las marcas no estan, se insertan dentro del contenedor vacio que
    el JavaScript va a sobreescribir. Idempotente: correrlo dos veces da
    el mismo archivo.
    """
    ini, fin = "<!--%s-->" % marca, "<!--/%s-->" % marca
    bloque = ini + "\n" + dentro + "\n" + fin
    if ini in html:
        return re.sub(re.escape(ini) + r".*?" + re.escape(fin), lambda _: bloque,
                      html, flags=re.S)
    raise SystemExit("falta el ancla %s" % marca)


# ---------------------------------------------------------------- precios
def bloque_precios():
    p = leer("data/precios.json")
    meta, cultivos = p["_meta"], p["cultivos"]
    fp = meta.get("fuente_principal", {})
    fd = meta.get("fuente_diaria", {})

    filas = []
    for c in sorted(cultivos, key=lambda c: c["nombre"]):
        # La unidad manda. Un numero de mayoreo sin el empaque al lado es
        # ilegible: 1,047 el ciento de aguacate y 1,047 la libra son dos
        # mundos. Si la fuente no la declaro, la celda queda vacia con su
        # raya, no se rellena con un supuesto.
        filas.append(
            "<tr>"
            "<th scope=\"row\">%s</th>"
            "<td>%s</td><td>%s</td>"
            "<td>%s</td><td>%s</td><td>%s</td>"
            "<td>%s</td>"
            "</tr>" % (
                esc(c["nombre"]),
                esc(c.get("unidad_mayorista") or "—"),
                rd(c.get("precio_mayorista")),
                esc(c.get("unidad_minorista") or "—"),
                rd(c.get("precio_minorista")),
                rd(c.get("precio_supermercado")),
                esc(c.get("fecha_mayorista") or "—"),
            ))

    tabla = (
        '<table class="tabla-estatica">'
        '<caption>Precios oficiales de %d productos agrícolas en República '
        'Dominicana. Mayorista según %s (edición %s); minorista y '
        'supermercado según el mismo informe. Cada fila lleva la fecha en '
        'que se midió el precio mayorista.</caption>'
        '<thead><tr>'
        '<th scope="col">Producto</th>'
        '<th scope="col">Empaque mayorista</th><th scope="col">Precio mayorista</th>'
        '<th scope="col">Empaque minorista</th><th scope="col">Precio minorista</th>'
        '<th scope="col">Supermercado</th>'
        '<th scope="col">Medido el</th>'
        '</tr></thead><tbody>%s</tbody></table>'
    ) % (len(cultivos), esc(fp.get("nombre", "fuente oficial")),
         esc(fp.get("edicion", "")), "".join(filas))

    # Dataset, no Product. Esto no es un catalogo de venta: es una tabla de
    # precios publicados por el Estado y reproducidos con su fuente. Marcarlo
    # como Product con "offers" seria declarar que Kcuesta los vende.
    ld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Precios oficiales del mercado agrícola dominicano",
        "description": meta.get("descripcion", ""),
        "url": BASE + "precios.html",
        "inLanguage": "es-DO",
        "isAccessibleForFree": True,
        # SIN `license`. Estaba declarado CC BY 4.0 y eso es afirmar derechos
        # sobre cifras del Ministerio y de MERCADOM, que no son nuestras. Lo
        # que sí es nuestro es la compilación y la normalización; si algún
        # día se quiere licenciar, hay que decir que cubre eso y no los
        # números de origen. Mientras tanto, `isBasedOn` y la atribución
        # visible dicen la verdad sin reclamar nada.
        "spatialCoverage": {"@type": "Country", "name": "República Dominicana"},
        # NO se pone `unitText`. Las unidades de este archivo son ocho
        # distintas —Ciento, UD, LB, Doc, Litro, Quintal— y estampar
        # "DOP/libra" en el marcado sería inventarle al dato una etiqueta
        # que la fuente nunca dio. La unidad va fila por fila en la tabla.
        "variableMeasured": [
            {"@type": "PropertyValue", "name": "Precio mayorista"},
            {"@type": "PropertyValue", "name": "Precio minorista"},
            {"@type": "PropertyValue", "name": "Precio de supermercado"}],
        "keywords": ["precios agrícolas", "República Dominicana", "mercado mayorista",
                     "agricultura", "canasta básica"],
        # La cobertura temporal es la EDICION del informe del Ministerio, no
        # el dia en que corrimos el pipeline. Decir "2026-08-16" cuando la
        # edicion es del 7 es fechar el dato con nuestro reloj.
        "temporalCoverage": fp.get("edicion"),
        "distribution": [{"@type": "DataDownload",
                          "contentUrl": BASE + "data/precios.json",
                          "encodingFormat": "application/json"}],
        "publisher": {"@type": "Organization", "name": "Kcuesta", "url": BASE},
        "dateModified": meta.get("actualizado"),
        "creator": {"@type": "Organization", "name": "Kcuesta", "url": BASE},
        "isBasedOn": [x for x in [
            {"@type": "Dataset", "name": fp.get("nombre"), "url": fp.get("url")} if fp.get("url") else None,
            {"@type": "Dataset", "name": fd.get("nombre"), "url": fd.get("url")} if fd.get("url") else None,
        ] if x],
    }
    return tabla, ld, meta.get("actualizado")


# ----------------------------------------------------------------- gremio
def bloque_gremio():
    idx = leer("data/partes.json")
    pubs = sorted([p for p in idx["partes"] if p.get("estado") == "publicado"],
                  key=lambda p: p["fecha"], reverse=True)
    if not pubs:
        raise SystemExit("sin partes publicados")
    parte = leer(pubs[0]["archivo"])
    CAT = leer("data/gremio-rubros.json")["rubros"]
    m = parte["_meta"]

    ETIQ = {"premium": "Prímium", "primera": "Primera", "segunda": "Segunda",
            "tercera": "Tercera", "regular": "Regular",
            "inferior": "Inferiores y viejos"}

    filas = []
    for i in parte.get("items", []):
        c = CAT.get(i["cultivo"], {})
        # La unidad del renglon manda sobre la del catalogo: el mismo rubro
        # se cotiza en dos empaques el mismo dia. Misma regla que gremio.js.
        unidad = i["unidad"] if "unidad" in i else c.get("unidad")
        libras = i["libras_unidad"] if "libras_unidad" in i else c.get("libras_unidad")
        por_lb = ("%s/lb" % rango(round(i["precio_min"] / libras, 2),
                                  round(i["precio_max"] / libras, 2), 2)) if libras else \
                 ("no se vende por peso" if unidad else "sin unidad declarada")
        filas.append(
            "<tr><th scope=\"row\">%s</th><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                esc(c.get("nombre") or i["cultivo"]),
                esc(ETIQ.get(i.get("calidad"), i.get("calidad") or "Precio del día")),
                rango(i["precio_min"], i["precio_max"], 0),
                esc(unidad or "no declarada"),
                esc(por_lb)))

    tabla = (
        '<table class="tabla-estatica">'
        '<caption>Parte al por mayor del %s en el %s, %s, publicado por la %s. '
        'Precios en pesos dominicanos, por el empaque que declaró el gremio.'
        '%s</caption>'
        '<thead><tr><th scope="col">Rubro</th><th scope="col">Grado</th>'
        '<th scope="col">Precio</th><th scope="col">Empaque</th>'
        '<th scope="col">Por libra</th></tr></thead><tbody>%s</tbody></table>'
    ) % (esc(fecha_larga(m["fecha"])), esc(m["plaza"]), esc(m["provincia"]),
         esc(m["fuente"]),
         (" " + esc(m["nota_plaza"])) if m.get("nota_plaza") else "",
         "".join(filas))

    ld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Parte de precios al por mayor del Mercado Nuevo de la Duarte",
        "description": ("Precios mayoristas diarios del Mercado Nuevo de la Duarte, "
                        "Santo Domingo, publicados por la %s y reproducidos con su "
                        "permiso. Con escalera de calidad y rango de plaza." % m["fuente"]),
        "url": BASE + "gremio.html",
        "inLanguage": "es-DO",
        "isAccessibleForFree": True,
        # El archivo tiene mas de un parte y el anterior es el que sostiene
        # la comparacion de subio/bajo. Se declara desde el mas viejo, en
        # rango abierto, y sale del indice — no escrito a mano, que es como
        # estas fechas se quedan viejas.
        "temporalCoverage": "%s/.." % min(p["fecha"] for p in pubs),
        "distribution": [{"@type": "DataDownload",
                          "contentUrl": BASE + "data/partes.json",
                          "encodingFormat": "application/json"}],
        "keywords": ["precios al por mayor", "Mercado Nuevo de la Duarte",
                     "República Dominicana", "mayorista", "agricultura"],
        "dateModified": m.get("actualizado", m["fecha"]),
        "spatialCoverage": {"@type": "Place", "name": "%s, %s, República Dominicana"
                            % (m["plaza"], m["provincia"])},
        "variableMeasured": "Precio mayorista por rubro y grado de calidad",
        "creator": {"@type": "Organization", "name": m["fuente"]},
        "publisher": {"@type": "Organization", "name": "Kcuesta", "url": BASE},
    }
    return tabla, ld, m.get("actualizado", m["fecha"])


# ---------------------------------------------------------------- mercado
def bloque_mercado():
    """La vitrina, para el que no ejecuta JavaScript.

    Solo salen las ofertas de GONDOLA (`data/ofertas.json`), que son precios
    reales capturados de las cadenas que publican catalogo. Los anuncios de
    productor de `data/anuncios.json` son ILUSTRATIVOS mientras no haya
    productores publicando, y meterlos aqui seria darle a Google una tienda
    inventada como si fuera un mercado con gente vendiendo.

    Tampoco se ordena por precio ni se corona la cadena mas barata: se
    ensena la banda del mercado (p25-p75) y cada rubro contra ella. Un
    ranking por precio no mide quien vende mejor, mide quien esta mas
    desesperado.
    """
    o = leer("data/ofertas.json")
    meta, rubros = o["_meta"], o["rubros"]

    filas = []
    for r in sorted(rubros, key=lambda r: r["nombre"]):
        banda = ("%s – %s" % (rd(r["p25_lb"], 2), num_es(r["p75_lb"], 2))
                 if r.get("p25_lb") is not None and r.get("p75_lb") is not None else "—")
        # La referencia mayorista NUNCA sale sin decir quien la midio ni
        # cuando. Es media pagina del argumento del sitio: la gondola
        # cuesta X y el mostrador mayorista cuesta Y, segun esta fuente,
        # medido este dia.
        ref = "—"
        if r.get("mercado_ref_unidad") is not None:
            ref = "%s/lb · %s" % (rd(r["mercado_ref_unidad"], 2),
                                  esc(r.get("mercado_ref_fuente") or "fuente sin declarar"))
            if r.get("mercado_ref_fecha"):
                ref += " · %s" % esc(r["mercado_ref_fecha"])
        filas.append(
            "<tr><th scope=\"row\">%s</th><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                esc(r["nombre"]),
                rango(r["precio_lb_min"], r["precio_lb_max"], 2) + "/lb"
                    if r.get("precio_lb_min") is not None else "no se vende por peso",
                banda, ref,
                ("+%d%%" % r["sobreprecio"]) if r.get("sobreprecio") else "—"))

    tabla = (
        '<table class="tabla-estatica">'
        '<caption>Precio de góndola de %d rubros agrícolas en supermercados '
        'dominicanos que publican su catálogo, comparado contra el mostrador '
        'mayorista. %s Actualizado el %s. La banda es el rango normal del '
        'mercado (p25–p75), no un ranking: no se corona la cadena más barata.'
        '</caption>'
        '<thead><tr><th scope="col">Rubro</th>'
        '<th scope="col">En góndola</th><th scope="col">Banda del mercado</th>'
        '<th scope="col">Referencia mayorista</th>'
        '<th scope="col">Sobreprecio</th></tr></thead>'
        '<tbody>%s</tbody></table>'
    ) % (len(rubros), esc(meta.get("descripcion", "")),
         esc(fecha_larga(meta["actualizado"])), "".join(filas))

    ld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Precios de góndola de supermercados dominicanos frente al mercado mayorista",
        "description": meta.get("descripcion", ""),
        "url": BASE + "mercado.html",
        "inLanguage": "es-DO",
        "isAccessibleForFree": True,
        "dateModified": meta.get("actualizado"),
        "spatialCoverage": {"@type": "Country", "name": "República Dominicana"},
        "variableMeasured": [
            {"@type": "PropertyValue", "name": "Precio al consumidor",
             "unitText": "DOP/libra"},
            {"@type": "PropertyValue", "name": "Banda del mercado (p25–p75)",
             "unitText": "DOP/libra"},
            {"@type": "PropertyValue", "name": "Sobreprecio sobre el mayorista",
             "unitText": "%"}],
        "keywords": ["precios de supermercado", "República Dominicana",
                     "góndola", "canasta básica", "agricultura"],
        "distribution": [{"@type": "DataDownload",
                          "contentUrl": BASE + "data/ofertas.json",
                          "encodingFormat": "application/json"}],
        "creator": {"@type": "Organization", "name": "Kcuesta", "url": BASE},
        "publisher": {"@type": "Organization", "name": "Kcuesta", "url": BASE},
    }
    return tabla, ld, meta.get("actualizado")


# --------------------------------------------------------------- portada
def bloque_portada():
    """La muestra de la portada.

    Sin JavaScript el bloque decia, literalmente, "Precios reales de
    supermercado. Cargando...". Ese era el unico texto con forma de precio
    en la pagina de prioridad 1.0 del sitio, y por tanto el candidato a
    salir de resumen en Google.
    """
    p = leer("data/portada.json")
    filas = "".join(
        "<tr><th scope=\"row\">%s</th><td>%s/lb</td><td>%s/lb</td><td>%s</td></tr>" % (
            esc(r["nombre"]),
            rango(r["precio_lb_min"], r["precio_lb_max"], 2),
            rd(r["mercado_ref_unidad"], 2) if r.get("mercado_ref_unidad") is not None else "—",
            ("+%d%%" % r["sobreprecio"]) if r.get("sobreprecio") else "—")
        for r in p["rubros"])
    return (
        '<table class="tabla-estatica">'
        '<caption>Muestra de %d de los %d rubros comparados, al %s.</caption>'
        '<thead><tr><th scope="col">Rubro</th><th scope="col">En góndola</th>'
        '<th scope="col">Mayorista</th><th scope="col">Sobreprecio</th>'
        '</tr></thead><tbody>%s</tbody></table>'
    ) % (len(p["rubros"]), p.get("total", len(p["rubros"])),
         esc(fecha_larga(p["_meta"]["actualizado"])), filas)

# ---------------------------------------------------------------- escribir
def inyectar(archivo, marca_tabla, tabla, ld=None):
    ruta = os.path.join(RAIZ, archivo)
    h = open(ruta, encoding="utf-8").read()
    h = entre_marcas(h, marca_tabla, tabla)
    # La portada ya trae su @graph escrito a mano; solo se le rellena la
    # muestra de precios.
    if ld is not None:
        h = entre_marcas(h, "ld", '<script type="application/ld+json">%s</script>'
                         % json.dumps(ld, ensure_ascii=False, separators=(",", ":")))
    open(ruta, "w", encoding="utf-8").write(h)


def _fecha_ipc():
    """El mes del último dato del Banco Central, como fecha. Si el archivo
    todavía no existe, se deja que el sitemap use la fecha de hoy."""
    try:
        with open(os.path.join(RAIZ, "data", "ipc.json"), encoding="utf-8") as f:
            return json.load(f)["_meta"]["ultimo_mes"] + "-01"
    except (OSError, KeyError, ValueError):
        return None


def sitemap(fechas):
    # lastmod real, sacado del dato. Escrito a mano envejece mal y le
    # ensena a Google que las fechas de este sitio no son de fiar.
    hoy = datetime.date.today().isoformat()
    paginas = [
        ("", "daily", "1.0", fechas.get("gremio", hoy)),
        ("mercado.html", "daily", "0.9", fechas.get("mercado", hoy)),
        ("gremio.html", "daily", "0.9", fechas.get("gremio", hoy)),
        ("precios.html", "daily", "0.8", fechas.get("precios", hoy)),
        # El IPC sale una vez al mes: su lastmod es el del dato, no el de hoy.
        ("inflacion.html", "monthly", "0.8", fechas.get("ipc") or hoy),
        ("vender.html", "monthly", "0.5", hoy),
    ]
    filas = "\n".join(
        "  <url><loc>%s%s</loc><lastmod>%s</lastmod>"
        "<changefreq>%s</changefreq><priority>%s</priority></url>"
        % (BASE, p, lm, cf, pr) for p, cf, pr, lm in paginas)
    open(os.path.join(RAIZ, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + filas + "\n</urlset>\n")


if __name__ == "__main__":
    tp, ldp, fp = bloque_precios()
    tg, ldg, fg = bloque_gremio()
    tm, ldm, fm = bloque_mercado()
    inyectar("precios.html", "tabla-precios", tp, ldp)
    inyectar("gremio.html", "tabla-gremio", tg, ldg)
    inyectar("mercado.html", "tabla-mercado", tm, ldm)
    inyectar("index.html", "tabla-portada", bloque_portada())
    sitemap({"precios": fp, "gremio": fg, "mercado": fm, "ipc": _fecha_ipc()})
    print("precios + gremio + mercado + portada + sitemap regenerados")
