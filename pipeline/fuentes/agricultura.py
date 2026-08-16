"""Ministerio de Agricultura — Informe de Precios Inter diarios.

Se publica lunes, miércoles y viernes siguiendo metodología OIMA. Es la
fuente más rica del país: el Cuadro 3 da, para el mismo producto y el mismo
día, el precio mayorista del Mercado Nuevo y el minorista de seis mercados
más el promedio de supermercados. Ese abanico es exactamente la brecha que
Kcuesta enseña — y ninguna de sus columnas es la finca.

Descubrimiento de la URL: el REST de WordPress está apagado en
agricultura.gob.do, así que no hay índice consultable. Se prueba el patrón
de fecha hacia atrás desde hoy y, si eso falla, se raspa la página de
archivo de la categoría.
"""

from __future__ import annotations

import datetime as dt
import logging
import re

from ..comun import FilaOficial, Resultado, guardar_crudo, pdf_a_texto, sesion, MESES
from ..config import ARCHIVO, TIMEOUT
from ..normalizar import a_numero, sin_tildes

log = logging.getLogger("kcuesta.agricultura")

FUENTE = "Ministerio de Agricultura"
BASE = "https://agricultura.gob.do/wp-content/uploads"
ARCHIVO_CAT = (
    "https://agricultura.gob.do/category/estadisticas-agropecuarias/"
    "precios-de-productos-agropecuarios/"
    "2-datos-inter-diarios-de-precios-de-mercados-y-supermercados-de-sto-dgo/"
)

MES_NOMBRE = {v: k for k, v in MESES.items() if k != "setiembre"}

# Las columnas del Cuadro 3, en el orden en que salen impresas.
MERCADOS_CUADRO3 = [
    "Mercado Nuevo", "CONAPROPE", "Los Mina",
    "Villa Consuelo", "Cristo Rey", "MERCADOM", "Supermercado",
]

UNIDADES = {"lb", "und", "doc", "litro", "quintal", "ciento", "millar", "unid", "kg", "u"}


def _urls_candidatas(fecha: dt.date) -> list[str]:
    """El nombre del archivo no es consistente: cambia mayúsculas del mes y
    la palabra 'precios'/'Precios'. Se prueban las variantes vistas."""
    mes = MES_NOMBRE[fecha.month]
    salida = []
    for palabra in ("Informe-de-Precios", "Informe-de-precios"):
        for m in (mes, mes.capitalize()):
            salida.append(f"{BASE}/{fecha:%Y/%m}/{palabra}-{fecha.day:02d}-de-{m}-{fecha.year}.pdf")
            salida.append(f"{BASE}/{fecha:%Y/%m}/{palabra}-{fecha.day}-de-{m}-{fecha.year}.pdf")
    return salida


def _buscar_pdf(s, hoy: dt.date, dias_atras: int = 10):
    """Devuelve (url, bytes, fecha) del informe más reciente que exista.

    Sondea con HEAD y en paralelo. Son hasta cuarenta combinaciones de fecha
    y variante de nombre; en serie con GET completo el descubrimiento tardaba
    más que el resto del pipeline junto.
    """
    from concurrent.futures import ThreadPoolExecutor

    candidatas: list[tuple[dt.date, str]] = []
    for delta in range(dias_atras):
        fecha = hoy - dt.timedelta(days=delta)
        if fecha.weekday() > 4:          # publican de lunes a viernes
            continue
        candidatas.extend((fecha, u) for u in _urls_candidatas(fecha))

    def existe(par):
        fecha, url = par
        try:
            resp = s.head(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200 and "pdf" in resp.headers.get("content-type", ""):
                return fecha, url
        except Exception:                # noqa: BLE001
            pass
        return None

    with ThreadPoolExecutor(max_workers=12) as pool:
        hallazgos = [h for h in pool.map(existe, candidatas) if h]

    if hallazgos:
        fecha, url = max(hallazgos, key=lambda h: h[0])   # el más reciente
        resp = s.get(url, timeout=TIMEOUT)
        if resp.status_code == 200 and resp.content.startswith(b"%PDF"):
            log.info("informe hallado: %s", url)
            return url, resp.content, fecha

    # Respaldo: la página de archivo de la categoría.
    log.info("patrón de fecha sin resultados; se raspa el archivo de la categoría")
    try:
        html = s.get(ARCHIVO_CAT, timeout=TIMEOUT).text
        enlaces = re.findall(r'href="([^"]*Informe-de-[Pp]recios[^"]*\.pdf)"', html)
        for url in enlaces[:5]:
            resp = s.get(url, timeout=TIMEOUT)
            if resp.status_code == 200 and resp.content.startswith(b"%PDF"):
                m = re.search(r"(\d{1,2})-de-([A-Za-zá-ú]+)-(\d{4})", url)
                fecha = hoy
                if m:
                    mes = MESES.get(sin_tildes(m.group(2).lower()), hoy.month)
                    fecha = dt.date(int(m.group(3)), mes, int(m.group(1)))
                log.info("informe hallado en archivo: %s", url)
                return url, resp.content, fecha
    except Exception as e:               # noqa: BLE001
        log.warning("raspado del archivo falló: %s", e)
    return None, None, None


def _campos(linea: str) -> list[str]:
    return [c.strip() for c in re.split(r"\s{2,}", linea.strip()) if c.strip()]


def _parsear_cuadro3(texto: str, fecha: dt.date, url: str) -> list[FilaOficial]:
    """Cuadro 3: un producto por fila, mayorista + siete columnas de mercado.

    No se leen posiciones de columna fijas — el ancho cambia entre ediciones.
    Se ancla en la unidad minorista ('lb', 'Und', 'Doc'), que siempre está
    justo antes del bloque de precios de mercado, y se cuenta desde ahí.
    """
    filas: list[FilaOficial] = []
    en_cuadro = False

    for linea in texto.splitlines():
        if "CONAPROPE" in linea and "CRISTO REY" in linea:
            en_cuadro = True
            continue
        if not en_cuadro:
            continue
        if re.search(r"CUADRO\s+4|F UE N T E|FUENTE\s*:", linea, re.I):
            en_cuadro = False
            continue

        campos = _campos(linea)
        if len(campos) < 4:
            continue

        # Índice de la unidad minorista: el último campo corto y alfabético.
        idx_unid = None
        for i, c in enumerate(campos):
            if sin_tildes(c).lower().strip(".") in UNIDADES:
                idx_unid = i
        if idx_unid is None or idx_unid == 0:
            continue

        nombre = campos[0]
        if not re.match(r"^[A-ZÁÉÍÓÚÑ]", nombre) or nombre.isupper() and len(nombre) < 4:
            continue

        unidad_min = campos[idx_unid]
        valores = campos[idx_unid + 1:]

        # A la izquierda de la unidad: empaque mayorista (texto) y su precio.
        izquierda = campos[1:idx_unid]
        empaque = next((c for c in izquierda if a_numero(c) is None and c not in {"-"}), None)
        precio_may = next((a_numero(c) for c in reversed(izquierda) if a_numero(c) is not None), None)

        if precio_may is not None and empaque:
            filas.append(FilaOficial(
                nombre_crudo=nombre, fecha=fecha, nivel="mayorista",
                unidad=empaque, precio=precio_may,
                fuente=FUENTE, fuente_url=url, mercado="Mercado Nuevo",
            ))

        for i, bruto in enumerate(valores[:len(MERCADOS_CUADRO3)]):
            precio = a_numero(bruto)
            if precio is None or precio <= 0:
                continue
            mercado = MERCADOS_CUADRO3[i]
            if mercado == "Supermercado":
                nivel = "supermercado"
            elif mercado == "Mercado Nuevo" and i == 0:
                nivel = "minorista"
            else:
                nivel = "minorista"
            filas.append(FilaOficial(
                nombre_crudo=nombre, fecha=fecha, nivel=nivel,
                unidad=unidad_min, precio=precio,
                fuente=FUENTE, fuente_url=url, mercado=mercado,
            ))
    return filas


def _parsear_colmados(texto: str, fecha: dt.date, url: str) -> list[FilaOficial]:
    """Cuadro de colmados: nueve barrios de Santo Domingo más un promedio.

    La tabla agrupa con celdas combinadas — 'Arroz' abarca las filas
    'Selecto' y 'Superior', y en el texto extraído esa etiqueta cae en una
    línea vecina, no en la suya. Reconstruir esa jerarquía por indentación
    es frágil y se rompe con cualquier reajuste de la plantilla, así que se
    guarda la variedad tal cual viene ('Selecto', 'Roja', 'Verde grande') y
    se deja que `cultivo_alias` la resuelva a mano. Ahí el mapeo es
    explícito y auditable, que es justo lo que la heurística no da.

    Se toma la última columna, 'Promedio Total', en vez de promediar los
    barrios: varios traen huecos y un promedio propio saldría distinto del
    publicado sin ninguna ganancia.
    """
    filas: list[FilaOficial] = []
    en_cuadro = False
    for linea in texto.splitlines():
        if re.search(r"en\s+Colmados\s+de\s+Santo\s+Domingo", linea, re.I):
            en_cuadro = True
            continue
        if not en_cuadro:
            continue
        if re.search(r"Carnicer|FUENTE\s*:|F UE N T E", linea, re.I):
            en_cuadro = False
            continue

        campos = _campos(linea)
        if len(campos) < 3:
            continue
        idx_unid = next(
            (i for i, c in enumerate(campos) if sin_tildes(c).lower().strip(".") in UNIDADES),
            None,
        )
        if idx_unid is None or idx_unid == 0:
            continue

        nombre = " ".join(campos[:idx_unid])
        promedio = a_numero(campos[-1])
        if promedio is None or promedio <= 0:
            continue
        filas.append(FilaOficial(
            nombre_crudo=nombre, fecha=fecha, nivel="colmado",
            unidad=campos[idx_unid], precio=promedio,
            fuente=FUENTE, fuente_url=url, mercado="Colmados de Santo Domingo",
        ))
    return filas


def capturar(hoy: dt.date | None = None) -> Resultado:
    hoy = hoy or dt.date.today()
    r = Resultado(fuente="agricultura")
    try:
        s = sesion()
        url, contenido, fecha = _buscar_pdf(s, hoy)
        if not contenido:
            r.error = "no se encontró ningún informe en los últimos 10 días"
            return r

        r.artefacto = guardar_crudo(f"agricultura-{fecha:%Y-%m-%d}.pdf", contenido, hoy)
        texto = pdf_a_texto(ARCHIVO.parent / r.artefacto)

        r.oficiales.extend(_parsear_cuadro3(texto, fecha, url))
        r.oficiales.extend(_parsear_colmados(texto, fecha, url))

        if not r.oficiales:
            r.error = "el informe se descargó pero no se reconoció ninguna fila"
        log.info("agricultura: %d filas, fecha del dato %s", len(r.oficiales), fecha)
    except Exception as e:               # noqa: BLE001
        r.error = f"{type(e).__name__}: {e}"
        log.error("agricultura falló: %s", r.error)
    return r
