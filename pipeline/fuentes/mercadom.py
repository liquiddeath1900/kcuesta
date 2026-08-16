"""MERCADOM — Merca Santo Domingo, precios de prensa.

La fuente más urgente de todas y la más frágil. Joomla con PhocaDownload
sirviendo UN solo archivo en la ranura `download=11:precios`, que se
sobrescribe cada vez que publican. No hay histórico, no hay archivo, no hay
forma de pedir el de ayer. El día que este script no corra, ese día no
existe.

Formato del PDF (una página, verificado 2026-08-16 con el del 12 de agosto):

    PRODUCTOS          UNIDAD DE MEDIDA   PRECIOS POR MAYOR   UNIDAD   PRECIOS DETALLE
    AJI CUBANELA              LB                     30.00      LB              35.00
"""

from __future__ import annotations

import datetime as dt
import logging
import re

from ..comun import FilaOficial, Resultado, guardar_crudo, pdf_a_texto, sesion, MESES
from ..config import ARCHIVO, TIMEOUT
from ..normalizar import a_numero

log = logging.getLogger("kcuesta.mercadom")

URL = "https://mercadom.gob.do/index.php/precios-msd?download=11:precios"
FUENTE = "MERCADOM — Merca Santo Domingo"

_RE_FECHA = re.compile(
    r"PRECIOS\s+DE\s+PRODUCTOS\s+DEL\s+(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚa-záéíóú]+)\s+DEL?\s+(\d{4})",
    re.I,
)
# producto ... unidad ... precio ... unidad ... precio
# El nombre puede traer espacios; las unidades son cortas y en mayúsculas.
_RE_FILA = re.compile(
    r"^\s*(?P<nombre>[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\s./()-]{2,60}?)\s{2,}"
    r"(?P<u1>[A-ZÁÉÍÓÚ/]{1,12})\s{2,}"
    r"(?P<p1>[\d,]+\.\d{2})\s{2,}"
    r"(?:(?P<u2>[A-ZÁÉÍÓÚ/]{1,12})\s{2,}(?P<p2>[\d,]+\.\d{2}))?\s*$"
)


def _fecha_del_informe(texto: str, respaldo: dt.date) -> dt.date:
    m = _RE_FECHA.search(texto)
    if not m:
        log.warning("no se pudo leer la fecha del PDF; se usa la de hoy")
        return respaldo
    dia, mes, ano = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    from ..normalizar import sin_tildes
    return dt.date(ano, MESES.get(sin_tildes(mes), respaldo.month), dia)


def capturar(hoy: dt.date | None = None) -> Resultado:
    hoy = hoy or dt.date.today()
    r = Resultado(fuente="mercadom")
    try:
        s = sesion()
        resp = s.get(URL, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        if not resp.content.startswith(b"%PDF"):
            r.error = f"la ranura no devolvió PDF (content-type={resp.headers.get('content-type')})"
            return r

        r.artefacto = guardar_crudo("mercadom-precios.pdf", resp.content, hoy)
        texto = pdf_a_texto(ARCHIVO.parent / r.artefacto)
        fecha = _fecha_del_informe(texto, hoy)

        if fecha != hoy:
            # Normal: publican con rezago y la ranura se queda con el último.
            log.info("MERCADOM trae datos del %s (hoy es %s)", fecha, hoy)

        for linea in texto.splitlines():
            m = _RE_FILA.match(linea)
            if not m:
                continue
            nombre = " ".join(m.group("nombre").split())
            mayor = a_numero(m.group("p1"))
            if mayor is not None:
                r.oficiales.append(FilaOficial(
                    nombre_crudo=nombre, fecha=fecha, nivel="mayorista",
                    unidad=m.group("u1"), precio=mayor,
                    fuente=FUENTE, fuente_url=URL, mercado="Merca Santo Domingo",
                ))
            detalle = a_numero(m.group("p2")) if m.group("p2") else None
            if detalle is not None:
                r.oficiales.append(FilaOficial(
                    nombre_crudo=nombre, fecha=fecha, nivel="minorista",
                    unidad=m.group("u2"), precio=detalle,
                    fuente=FUENTE, fuente_url=URL, mercado="Merca Santo Domingo",
                ))

        if not r.oficiales:
            r.error = "el PDF se descargó pero no se reconoció ninguna fila"
        log.info("mercadom: %d filas, fecha del dato %s", len(r.oficiales), fecha)
    except Exception as e:            # noqa: BLE001 — un fallo aquí no puede tumbar el resto
        r.error = f"{type(e).__name__}: {e}"
        log.error("mercadom falló: %s", r.error)
    return r
