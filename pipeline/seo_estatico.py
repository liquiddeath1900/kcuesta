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
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "spatialCoverage": {"@type": "Country", "name": "República Dominicana"},
        "variableMeasured": "Precio mayorista, minorista y de supermercado por producto agrícola",
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
        "temporalCoverage": m["fecha"],
        "dateModified": m.get("actualizado", m["fecha"]),
        "spatialCoverage": {"@type": "Place", "name": "%s, %s, República Dominicana"
                            % (m["plaza"], m["provincia"])},
        "variableMeasured": "Precio mayorista por rubro y grado de calidad",
        "creator": {"@type": "Organization", "name": m["fuente"]},
        "publisher": {"@type": "Organization", "name": "Kcuesta", "url": BASE},
    }
    return tabla, ld, m.get("actualizado", m["fecha"])


# ---------------------------------------------------------------- escribir
def inyectar(archivo, marca_tabla, tabla, ld):
    ruta = os.path.join(RAIZ, archivo)
    h = open(ruta, encoding="utf-8").read()
    h = entre_marcas(h, marca_tabla, tabla)
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
        ("mercado.html", "daily", "0.9", fechas.get("precios", hoy)),
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
    inyectar("precios.html", "tabla-precios", tp, ldp)
    inyectar("gremio.html", "tabla-gremio", tg, ldg)
    sitemap({"precios": fp, "gremio": fg, "ipc": _fecha_ipc()})
    print("precios.html + gremio.html + sitemap.xml regenerados")
