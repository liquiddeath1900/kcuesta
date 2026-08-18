"""IPC por artículos del Banco Central — el contexto, no el precio.

Corre aparte de `pipeline.run` a propósito. Las demás fuentes devuelven
filas de PRECIO y terminan en las tablas de precios; esto no es un precio.
Es un ÍNDICE al consumidor, base octubre 2019 – septiembre 2020 = 100, y si
entrara por el mismo camino que MERCADOM tarde o temprano un 228.5 de yuca
acabaría pintado como RD$228.50 en una tarjeta. Sale a su propio archivo,
`data/ipc.json`, y solo lo lee inflacion.html.

Qué es y qué no es:

  * Es precio al CONSUMIDOR (colmado y supermercado), promedio nacional.
    No es mayorista, no es finca, y no se puede restar contra el parte del
    Mercado Nuevo como si fueran la misma vara.
  * Es mensual y sale unos diez días después de cerrar el mes. No sustituye
    a nadie del pipeline diario: los acompaña con la tendencia larga.
  * De los 364 artículos de la canasta aquí solo entran los ~35 que son
    producto agrícola crudo, o sea los que se corresponden con un rubro de
    Kcuesta. El pan y el salami también son alimento pero no son cosecha.

El Excel se lee con la librería estándar —un .xlsx es un zip de XML— para
no meterle una dependencia más a la Action por un archivo al mes.

    python -m pipeline.ipc [--local]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .comun import guardar_crudo, sesion
from .config import ARCHIVO, DATOS, TIMEOUT

log = logging.getLogger("kcuesta.ipc")

URL = ("https://cdn.bancentral.gov.do/documents/estadisticas/precios/"
       "documents/ipc_articulos_base_2019-2020.xlsx")
FUENTE = "Banco Central de la República Dominicana"
SERIE = "Índice de Precios al Consumidor por artículos"
BASE = "octubre 2019 – septiembre 2020 = 100"

MESES = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5,
         "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9,
         "Octubre": 10, "Noviembre": 11, "Diciembre": 12}

# El grupo entero de alimentos. Es el titular de la página: una sola cifra
# que contesta "¿está más cara la comida que el año pasado?".
GRUPO_ALIMENTOS = "01"

# Mapa a mano, igual que el alias de cultivos y por la misma razón: el
# parecido de los nombres miente. El IPC tiene UN artículo "Ajíes" donde
# Kcuesta tiene cuatro ajíes distintos, y "Aguacate" donde nosotros
# separamos benny, carla, criollo y popenoe. Por eso `rubros` es una lista:
# el índice cubre a todos ellos junto, y ninguna tarjeta de variedad puede
# rotularse con este número como si fuera suyo.
#
# Los que llevan artículo femenino. La página escribe la frase en palabras
# —"42 % más cara que hace un año"— y sin esto la yuca sale "más caro".
FEMENINOS = {
    "yuca", "papa", "batata", "cebolla", "lechuga", "zanahoria", "tayota",
    "berenjena", "auyama", "chinola", "naranja", "pina", "lechosa", "yautia",
    "habichuela-pinta", "habichuela-roja", "habichuela-negra",
}

# codigo BCRD: (id, nombre para leer, categoria, rubros de Kcuesta)
ARTICULOS = {
    "0111401": ("arroz", "Arroz", "granos", ["arroz-selecto", "arroz-superior", "arroz-super-selecto"]),
    "0116101": ("platano-verde", "Plátano verde", "viveres", ["platano-fhia20", "platano-barahonero", "platano-enano", "platano-macho"]),
    "0116104": ("platano-maduro", "Plátano maduro", "viveres", ["platano-maduro"]),
    "0116102": ("guineo-verde", "Guineo verde", "frutas", ["guineo-verde"]),
    "0116108": ("guineo-maduro", "Guineo maduro", "frutas", []),
    "0116103": ("aguacate", "Aguacate", "frutas", ["aguacate-benny", "aguacate-carla", "aguacate-criollo", "aguacate-popenoe"]),
    "0116105": ("lechosa", "Lechosa", "frutas", ["lechosa", "lechosa-maradol"]),
    "0116106": ("naranja", "Naranja", "frutas", ["naranja-dulce", "naranja-agria"]),
    "0116107": ("limon", "Limón agrio", "frutas", ["limon-criollo", "limon-persa"]),
    "0116109": ("pina", "Piña", "frutas", ["pina-md2"]),
    "0116112": ("chinola", "Chinola", "frutas", ["chinola"]),
    "0116201": ("coco-seco", "Coco seco", "frutas", ["coco-seco"]),
    "0117101": ("habichuela-pinta", "Habichuela pinta", "granos", ["habichuela-pinta"]),
    "0117102": ("habichuela-roja", "Habichuela roja", "granos", ["habichuela-roja"]),
    "0117104": ("habichuela-negra", "Habichuela negra", "granos", ["habichuela-negra"]),
    "0117103": ("guandul-verde", "Guandul verde", "granos", ["guandul-verde"]),
    "0117201": ("yuca", "Yuca", "viveres", ["yuca-bilin"]),
    "0117202": ("papa", "Papa", "viveres", ["papa"]),
    "0117203": ("name", "Ñame", "viveres", ["name-jamaiquino", "name-mina"]),
    "0117204": ("yautia", "Yautía", "viveres", ["yautia-amarilla", "yautia-blanca", "yautia-coco"]),
    "0117205": ("batata", "Batata", "viveres", ["batata-tifey"]),
    "0117301": ("cebolla", "Cebolla", "vegetales", ["cebolla-amarilla", "cebolla-roja"]),
    "0117302": ("ajo", "Ajo", "vegetales", ["ajo-importado"]),
    "0117303": ("aji", "Ají", "vegetales", ["aji-cachucha", "aji-cubanela", "aji-gustoso", "aji-morron"]),
    "0117304": ("tomate", "Tomate", "vegetales", ["tomate-bugalu", "tomate-ensalada"]),
    "0117305": ("berenjena", "Berenjena", "vegetales", ["berenjena"]),
    "0117306": ("auyama", "Auyama", "vegetales", ["auyama"]),
    "0117307": ("lechuga", "Lechuga", "vegetales", ["lechuga"]),
    "0117308": ("repollo", "Repollo", "vegetales", []),
    "0117309": ("zanahoria", "Zanahoria", "vegetales", ["zanahoria"]),
    "0117310": ("tayota", "Tayota", "vegetales", ["tayota"]),
    "0117311": ("apio", "Apio", "vegetales", ["apio"]),
    "0117312": ("pepino", "Pepino", "vegetales", ["pepino"]),
    "0117313": ("brocoli-coliflor", "Brócoli y coliflor", "vegetales", ["brocoli", "coliflor"]),
    "0121101": ("cafe", "Café", "granos", []),
}

# Cuántos meses de serie viajan al navegador. Seis años completos son 70
# puntos por rubro y no caben en el presupuesto de la página; dos años
# bastan para dibujar la línea y para el "vs. el año pasado".
MESES_VISIBLES = 24


# ---------------------------------------------------------------- xlsx


def _columna(ref: str) -> int:
    """'BC12' -> 54. La letra es base 26 sin cero."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _hojas(z: zipfile.ZipFile) -> dict[str, str]:
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    nsr = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    rels = {r.get("Id"): r.get("Target")
            for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    salida = {}
    for h in ET.fromstring(z.read("xl/workbook.xml")).iter(f"{ns}sheet"):
        destino = rels[h.get(f"{nsr}id")].lstrip("/")
        salida[h.get("name")] = destino if destino.startswith("xl/") else "xl/" + destino
    return salida


def _leer_hoja(ruta: Path, nombre_hoja: str) -> list[list]:
    """Devuelve la hoja como lista de filas; cada celda es str o float."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(ruta) as z:
        cadenas = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{ns}si"):
                cadenas.append("".join(t.text or "" for t in si.iter(f"{ns}t")))
        filas = []
        for fila in ET.fromstring(z.read(_hojas(z)[nombre_hoja])).iter(f"{ns}row"):
            celdas: list = []
            for c in fila.iter(f"{ns}c"):
                i = _columna(c.get("r") or "")
                while len(celdas) <= i:
                    celdas.append(None)
                # El texto suelto no viaja en <v> sino en <is><t>, así que
                # se atiende antes de exigir que haya <v>.
                if c.get("t") == "inlineStr":
                    celdas[i] = "".join(t.text or "" for t in c.iter(f"{ns}t"))
                    continue
                v = c.find(f"{ns}v")
                if v is None or v.text is None:
                    continue
                if c.get("t") == "s":
                    celdas[i] = cadenas[int(v.text)]
                else:
                    try:
                        celdas[i] = float(v.text)
                    except ValueError:
                        celdas[i] = v.text
            filas.append(celdas)
    return filas


# ---------------------------------------------------------------- serie


def _cabecera(filas: list[list]) -> int:
    """Fila donde empiezan los rótulos. No se cuenta desde arriba porque el
    Excel trae filas vacías de adorno que van cambiando de número."""
    for i, f in enumerate(filas[:20]):
        if f and str(f[0] or "").strip() == "Grupo":
            return i
    raise RuntimeError("no se encontró la fila de rótulos; cambió el formato")


def _fila_anios(filas: list[list], cab: int) -> list:
    """La fila de años, buscada hacia arriba desde los rótulos. No se cuenta
    "dos más arriba" porque las filas vacías de adorno no llegan todas al
    XML y el número de fila del Excel no es el del índice de la lista."""
    for i in range(cab - 1, -1, -1):
        for v in filas[i][6:]:
            try:
                if 2000 <= int(float(v)) <= 2100:
                    return filas[i]
            except (TypeError, ValueError):
                continue
    raise RuntimeError("no se encontró la fila de años; cambió el formato")


def _meses(filas: list[list]) -> list[tuple[int, str]]:
    """Columnas de la hoja -> ('2026-07'). El año solo aparece en la
    primera columna de ese año; el mes, en todas."""
    cab = _cabecera(filas)
    meses = filas[cab]
    anios = _fila_anios(filas, cab)
    cols, anio = [], None
    for j in range(6, max(len(anios), len(meses))):
        a = anios[j] if j < len(anios) else None
        if a:
            anio = int(float(a)) if not isinstance(a, str) else int(a.strip())
        m = meses[j] if j < len(meses) else None
        if isinstance(m, str) and m.strip() in MESES and anio:
            cols.append((j, f"{anio}-{MESES[m.strip()]:02d}"))
    return cols


def _codigo(celda) -> str:
    m = re.match(r"^\s*(\d{2,7})\b", str(celda or ""))
    return m.group(1) if m else ""


def _variacion(a, b) -> float | None:
    if a is None or b in (None, 0):
        return None
    return round((a / b - 1) * 100, 1)


def _mes_previo(clave: str) -> str:
    anio, mes = int(clave[:4]), int(clave[5:7])
    return f"{anio - 1}-12" if mes == 1 else f"{anio}-{mes - 1:02d}"


def _mediana(v: list[float]) -> float:
    o = sorted(v)
    n = len(o)
    return o[n // 2] if n % 2 else (o[n // 2 - 1] + o[n // 2]) / 2


def _estacionalidad(serie: dict[str, float]) -> dict[str, float]:
    """En qué meses del año el precio suele subir o bajar: la variación
    mes contra mes anterior, agrupada por número de mes.

    Se toma la MEDIANA y no el promedio. Son seis años nada más: a la yuca
    un enero se le fue el precio 40 % y con promedio ese solo año le pintaba
    a enero una subida de 16 % que no es la costumbre del rubro, es un mal
    año. La mediana lo deja donde pertenece, en el borde.

    Aun así son pocos años. Sirve para la forma —cuándo entra la cosecha y
    afloja el precio— no para creerle el decimal a un mes suelto.
    """
    k = sorted(serie)
    por_mes: dict[int, list[float]] = {}
    for i in range(1, len(k)):
        # Solo cuenta si el mes anterior es de verdad el mes anterior. Con
        # un hueco en la serie, comparar marzo contra el enero siguiente
        # daría un salto inventado de doce meses disfrazado de uno.
        if _mes_previo(k[i]) != k[i - 1]:
            continue
        previo = serie[k[i - 1]]
        if previo:
            por_mes.setdefault(int(k[i][5:7]), []).append(serie[k[i]] / previo - 1)
    return {f"{m:02d}": round(_mediana(v) * 100, 1)
            for m, v in sorted(por_mes.items()) if v}


def construir(ruta: Path) -> dict:
    hoja = next(n for n in _hojas(zipfile.ZipFile(ruta)) if n.startswith("2020-"))
    filas = _leer_hoja(ruta, hoja)
    cols = _meses(filas)
    primera = _cabecera(filas) + 1
    if not cols:
        raise RuntimeError("no se reconoció ninguna columna de mes; cambió el formato")

    rubros, alimentos = [], None
    for f in filas[primera:]:
        # El artículo va en la columna E; los grupos y subgrupos, a su
        # izquierda. El titular sale del grupo 01, que vive en la columna A.
        grupo = _codigo(f[0] if len(f) > 0 else None)
        articulo = _codigo(f[4] if len(f) > 4 else None)

        serie = {et: round(float(f[j]), 2)
                 for j, et in cols if j < len(f) and isinstance(f[j], float)}
        if len(serie) < 13:
            continue
        k = sorted(serie)

        if grupo == GRUPO_ALIMENTOS and alimentos is None:
            alimentos = {"mes": k[-1],
                         "interanual": _variacion(serie[k[-1]], serie[k[-13]]),
                         "mensual": _variacion(serie[k[-1]], serie[k[-2]])}
            continue
        if articulo not in ARTICULOS:
            continue

        ident, nombre, categoria, ligados = ARTICULOS[articulo]
        recientes = k[-MESES_VISIBLES:]
        rubros.append({
            "id": ident,
            "nombre": nombre,
            "categoria": categoria,
            "genero": "f" if ident in FEMENINOS else "m",
            "rubros_kcuesta": ligados,
            "codigo_bcrd": articulo,
            "articulo_bcrd": str(f[4]).split(" ", 1)[1].strip(),
            # Cuánto pesa en el gasto del hogar dominicano, en % de la
            # canasta. Es lo que dice si el rubro mueve el bolsillo de la
            # gente o solo el de quien lo siembra.
            "ponderacion": round(float(f[5]), 3),
            "indice": serie[k[-1]],
            "mensual": _variacion(serie[k[-1]], serie[k[-2]]),
            "interanual": _variacion(serie[k[-1]], serie[k[-13]]),
            "desde_base": _variacion(serie[k[-1]], 100),
            "meses": recientes,
            "serie": [serie[m] for m in recientes],
            "estacionalidad": _estacionalidad(serie),
        })

    rubros.sort(key=lambda r: r["nombre"])
    return {
        "_meta": {
            "fuente": FUENTE,
            "serie": SERIE,
            "base": BASE,
            "url": URL,
            "nivel": "precio al consumidor, promedio nacional",
            "cadencia": "mensual, ~10 días después de cerrar el mes",
            "ultimo_mes": max(r["meses"][-1] for r in rubros) if rubros else None,
            "capturado": dt.date.today().isoformat(),
            "advertencia": (
                "Es un índice, no un precio: dice cuánto cambió, no cuánto "
                "cuesta. Y es precio al consumidor, no mayorista ni de finca."
            ),
            "generado_por": "pipeline/ipc.py",
        },
        "alimentos": alimentos,
        "rubros": rubros,
    }


def capturar(local: bool = False) -> Path:
    destino = ARCHIVO / "bcrd" / "ipc_articulos.xlsx"
    if local and destino.exists():
        return destino
    log.info("bajando %s", URL)
    r = sesion().get(URL, timeout=TIMEOUT)
    r.raise_for_status()
    guardar_crudo("bcrd_ipc_articulos.xlsx", r.content)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(r.content)
    return destino


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.ipc")
    ap.add_argument("--local", action="store_true",
                    help="usa el xlsx ya bajado en archivo/bcrd/")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    datos = construir(capturar(args.local))
    salida = DATOS / "ipc.json"
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))
    log.info("%s — %d rubros, último mes %s, %.1f KB",
             salida.name, len(datos["rubros"]),
             datos["_meta"]["ultimo_mes"], salida.stat().st_size / 1024)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
