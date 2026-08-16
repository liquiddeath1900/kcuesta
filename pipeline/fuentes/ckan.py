"""Portal de Datos Abiertos (datos.gob.do) — serie histórica 2017 a la fecha.

Dataset "Informe Precios de Mercado Interdiario": dos CSV, mayorista y
minorista, con casi 44 mil filas que arrancan en agosto de 2017. Es el
respaldo con el que se siembra la base; no sirve para el día a día porque
llega con cerca de un mes de rezago y su grano es semana-del-mes, no fecha.

Trampas del archivo, todas verificadas:
  * delimitador punto y coma, no coma
  * codificación latin-1 ('S\\xfaper Selecto'), no UTF-8
  * los nombres traen comas sin comillas, así que leerlo por comas lo parte mal
  * la fecha viene como ('Primera', 'Agosto', 2017), no como fecha
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import logging

from ..comun import FilaOficial, Resultado, guardar_crudo, sesion
from ..config import TIMEOUT
from ..normalizar import a_numero, sin_tildes

log = logging.getLogger("kcuesta.ckan")

FUENTE = "Portal de Datos Abiertos — Ministerio de Agricultura"
BUSQUEDA = "https://datos.gob.do/api/3/action/package_search?q=precios+agropecuarios&rows=5"

# La fuente da semana del mes, no fecha. Se ancla cada semana a un día
# representativo. Es una aproximación y se dice: esta serie es para
# tendencia histórica, nunca para cotizar el día de hoy.
SEMANAS = {"primera": 4, "segunda": 11, "tercera": 18, "cuarta": 25, "quinta": 28}
MESES_CSV = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def _recursos() -> list[tuple[str, str]]:
    """Devuelve [(nivel, url)] de los CSV mayorista y minorista."""
    s = sesion()
    datos = s.get(BUSQUEDA, timeout=TIMEOUT).json()
    salida = []
    for paquete in datos["result"]["results"]:
        if "interdiario" not in sin_tildes(paquete["title"]).lower():
            continue
        for r in paquete.get("resources", []):
            if r.get("format", "").upper() != "CSV":
                continue
            nombre = sin_tildes(r.get("name", "")).lower()
            nivel = "mayorista" if "mayorista" in nombre else "minorista"
            salida.append((nivel, r["url"]))
    return salida


def _fecha(semana: str, mes: str, ano: str) -> dt.date | None:
    try:
        d = SEMANAS.get(sin_tildes(semana).strip().lower(), 15)
        m = MESES_CSV.get(sin_tildes(mes).strip().lower())
        a = int(str(ano).strip())
        if not m:
            return None
        return dt.date(a, m, d)
    except (ValueError, TypeError):
        return None


def capturar(hoy: dt.date | None = None) -> Resultado:
    hoy = hoy or dt.date.today()
    r = Resultado(fuente="ckan")
    try:
        s = sesion()
        recursos = _recursos()
        if not recursos:
            r.error = "el catálogo CKAN no devolvió ningún CSV del dataset interdiario"
            return r

        for nivel, url in recursos:
            resp = s.get(url, timeout=TIMEOUT * 2)
            resp.raise_for_status()
            r.artefacto = guardar_crudo(f"ckan-{nivel}.csv", resp.content, hoy)

            texto = resp.content.decode("latin-1")
            lector = csv.reader(io.StringIO(texto), delimiter=";")
            for campos in lector:
                # nombre ; categoria ; nivel ; unidad ; precio ; semana ; mes ; año
                if len(campos) < 8:
                    continue
                nombre = campos[0].strip()
                precio = a_numero(campos[4])
                fecha = _fecha(campos[5], campos[6], campos[7])
                if not nombre or precio is None or precio <= 0 or fecha is None:
                    continue
                nivel_fila = sin_tildes(campos[2]).strip().lower()
                r.oficiales.append(FilaOficial(
                    nombre_crudo=nombre, fecha=fecha,
                    nivel="mayorista" if "mayorista" in nivel_fila else "minorista",
                    unidad=campos[3].strip(), precio=precio,
                    fuente=FUENTE, fuente_url=url, mercado="Serie histórica",
                ))

        if not r.oficiales:
            r.error = "los CSV se descargaron pero no se reconoció ninguna fila"
        log.info("ckan: %d filas históricas", len(r.oficiales))
    except Exception as e:               # noqa: BLE001
        r.error = f"{type(e).__name__}: {e}"
        log.error("ckan falló: %s", r.error)
    return r
