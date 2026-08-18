"""Normalización de nombres y unidades.

Es la pieza que decide si el pipeline sirve o produce basura ordenada.
El mismo plátano aparece como:

    'PLATANO VERDE'                (MERCADOM, mayúsculas, sin tilde)
    'Platano Verde Und'            (Sirena, con el empaque pegado al nombre)
    'Plátano (Barahona), grande'   (Ministerio, calidad entre paréntesis)
    'Plátano Verde, Und'           (Nacional)

`clave()` los lleva a todos a la misma cadena canónica. Esa cadena se busca
en la tabla `cultivo_alias`, que se llena A MANO desde la lista que imprime
la corrida en seco. Deliberadamente no hay fuzzy match: emparejar
'ají cubanela' con 'ají gustoso' por parecido de cadena mete un precio
equivocado en la serie, y un precio equivocado es peor que un hueco.
"""

import re
import unicodedata

# Palabras de empaque y calidad que las fuentes pegan al nombre y que no
# distinguen un cultivo de otro.
#
# 'criollo', 'importado' y 'nacional' NO están aquí, aunque parezcan
# adjetivos de relleno: en el mercado dominicano marcan variedades con
# precios muy distintos. El ajo importado y el criollo no cuestan lo mismo,
# y el propio catálogo del Ministerio los lista por separado. Borrarlos
# fundía dos series en una.
RUIDO = {
    "und", "unidad", "unidades", "u", "uds",
    "lb", "lbs", "libra", "libras",
    "kg", "kilo", "kilos", "gr", "g", "gramos",
    "primera", "segunda", "1a", "2a", "1ra", "2da",
    "grande", "mediano", "mediana", "pequeno", "pequena",
    "fresco", "fresca", "frescos", "frescas",
    "de", "del", "la", "el", "los", "las", "y", "en", "por", "con", "a",
    "paquete", "bolsa", "funda", "bandeja", "empaque", "saco", "caja",
    "aprox", "approx", "x", "c/u", "cu",
}


def sin_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def clave(nombre: str) -> str:
    """Lleva un nombre de producto a su forma canónica de búsqueda.

    'Plátano (Barahona), grande' -> 'platano barahona'
    'PLATANO VERDE'              -> 'platano verde'
    'Platano Verde Und'          -> 'platano verde'
    """
    t = sin_tildes(nombre or "").lower()
    t = t.replace("ñ", "n")
    # Los paréntesis casi siempre traen la variedad, que sí distingue
    # ('Plátano (Barahona)' no es 'Plátano (Maeño)'), así que se abren en
    # vez de descartarse.
    t = re.sub(r"[()\[\]{}]", " ", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    palabras = [p for p in t.split() if p and p not in RUIDO and not p.isdigit()]
    return " ".join(palabras).strip()


# ------------------------------------------------------------------
# Unidades
# ------------------------------------------------------------------
# Cuántas unidades vendibles trae cada empaque mayorista. Sin esto no se
# puede comparar un millar de plátanos contra el plátano suelto del
# supermercado, que es exactamente la comparación que Kcuesta vende.
EMPAQUES = {
    "millar": 1000,
    "ciento": 100,
    "quintal": 100,          # 100 lb
    "qq": 100,
    "docena": 12,
    "doc": 12,
    "unidad": 1,
    "und": 1,
    "un": 1,
    "libra": 1,
    "lb": 1,
    "kilo": 2.20462,         # a libras
    "kg": 2.20462,
    "litro": 1,
    "fardo": 12,
}

_RE_SACO = re.compile(r"(?:saco|huacal|caja|funda)\s*(?:de\s*)?(\d+(?:[.,]\d+)?)\s*(lb|libras?|und|unidades?|u)\b", re.I)


def unidades_por_empaque(unidad: str) -> float | None:
    """Divisor para pasar de precio por empaque a precio por unidad vendible.

    'Millar'            -> 1000
    'Saco de 50 lb'     -> 50
    'Huacal de 45 lb'   -> 45
    'Saco de 600 und'   -> 600
    'Libra'             -> 1
    """
    if not unidad:
        return None
    u = sin_tildes(unidad).lower().strip()

    m = _RE_SACO.search(u)
    if m:
        return float(m.group(1).replace(",", "."))

    # 'Fardo/12 Ud', 'Saco/100 libra' — la forma con barra del CSV oficial.
    m = re.search(r"/\s*(\d+(?:[.,]\d+)?)", u)
    if m:
        return float(m.group(1).replace(",", "."))

    for palabra, factor in EMPAQUES.items():
        if re.search(rf"\b{palabra}\b", u):
            return float(factor)
    return None


def precio_por_unidad(precio: float, unidad: str) -> float | None:
    """Precio normalizado a la unidad vendible. None si no se sabe convertir.

    Devolver None a propósito en vez de asumir 1: un quintal tratado como
    libra mete un error de 100x en el índice y nadie lo nota hasta que un
    productor cotiza contra él.
    """
    div = unidades_por_empaque(unidad)
    if not div or div <= 0 or precio is None:
        return None
    return round(float(precio) / div, 4)


def a_numero(texto) -> float | None:
    """Convierte '1,234.50', ' 11,500.00 ', '(25.00)' o '-' a float.

    Los cuadros del Ministerio traen los negativos entre paréntesis, al
    estilo contable, y los huecos como guion.
    """
    if texto is None:
        return None
    if isinstance(texto, (int, float)):
        return float(texto)
    t = str(texto).strip()
    if not t or t in {"-", "–", "—", "N/D", "ND", "nd"}:
        return None
    negativo = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace(",", "").replace("RD$", "").replace("$", "").strip()
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if negativo else v


# ------------------------------------------------------------------
# Tamaño del empaque leído del título del producto
# ------------------------------------------------------------------
# Sin esto la comparación miente. La cadena vende la cebolla suelta por
# libra a RD$46 y en saco de 50 lb a RD$10,750, y agrupados sin normalizar
# el rubro dice "RD$46 – RD$10,750", como si el saco fuera 200 veces más
# caro cuando en realidad sale a RD$215 la libra... más caro igual, pero por
# 4.7x, no por 234x. Un rango así no se puede leer y además es falso.
#
# Se devuelve None cuando no se puede saber. Igual que con las unidades del
# mayorista: asumir 1 libra mete un error silencioso, y un hueco se ve.

_A_LIBRAS = {
    "lb": 1.0, "lbs": 1.0, "libra": 1.0, "libras": 1.0,
    "oz": 1 / 16, "onza": 1 / 16, "onzas": 1 / 16,
    "kg": 2.20462, "kilo": 2.20462, "kilos": 2.20462,
    "g": 0.00220462, "gr": 0.00220462, "gramo": 0.00220462, "gramos": 0.00220462,
}

# '22 lb', 'Aprox. 47–50 lb', '8oz', '1 kg', '500 g'
_RE_PESO = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:[-–—a]\s*(\d+(?:[.,]\d+)?)\s*)?"
    r"(lbs?|libras?|oz|onzas?|kgs?|kilos?|gr?a?m?o?s?)\b",
    re.I,
)
# '6 Packs de 24 oz', '3 x 500 g' — hay que multiplicar
_RE_MULTI = re.compile(r"(\d+)\s*(?:packs?|paq\w*|x|und|unidades)\s*(?:de\s*)?$", re.I)

# 'Aji Cubanela,Lb', 'Filete De Pechuga Pollo Cibao Lb', '– Libra (Aprox. ...)'
# La cadena lo vende POR libra y no pone número. Es una libra.
_RE_POR_LIBRA = re.compile(r"(?:^|[,\s(–-])\s*(?:lbs?|libras?)\b", re.I)


def libras_de_titulo(titulo: str) -> float | None:
    """Cuántas libras trae el empaque, leídas del nombre del producto.

    'Pera Forelle Fresca – Caja 22 lb'            -> 22.0
    'Papa Fresca – Saco (Aprox. 47–50 lb)'        -> 48.5   (promedio del rango)
    'Ají Gustoso Fresco – Pack 8oz'               -> 0.5
    'Papas Gold – Caja Retail (6 Packs de 24 oz)' -> 9.0    (6 × 24 oz)
    'Limón Verde Tahití – Caja y Malla'           -> None   (no dice cuánto)
    """
    if not titulo:
        return None
    t = sin_tildes(titulo)

    m = _RE_PESO.search(t)
    if not m:
        # Sin número pero con 'Lb' o 'Libra' suelto: se vende por libra.
        return 1.0 if _RE_POR_LIBRA.search(t) else None

    bajo = float(m.group(1).replace(",", "."))
    alto = float(m.group(2).replace(",", ".")) if m.group(2) else None
    cantidad = (bajo + alto) / 2 if alto else bajo

    unidad = m.group(3).lower()
    factor = next((v for k, v in _A_LIBRAS.items() if unidad.startswith(k)), None)
    if factor is None:
        return None
    libras = cantidad * factor

    # Multiplicador antes del peso: '6 Packs de 24 oz'.
    mult = _RE_MULTI.search(t[:m.start()])
    if mult:
        n = int(mult.group(1))
        if 1 < n <= 60:                 # más de 60 suele ser el año o un código
            libras *= n

    return round(libras, 4) if 0.005 <= libras <= 500 else None


def _segmentos(categoria: str) -> list[str]:
    """Parte 'Supermercado/Frutas y Vegetales/Víveres' en sus tramos."""
    bruto = re.split(r"[/>|]", sin_tildes(categoria or "").lower())
    return [s.strip(" .-") for s in bruto if s.strip(" .-")]


def _palabras(segmento: str) -> list[str]:
    return [p for p in re.split(r"[\s,&;]+", segmento) if p]


def _califica(categoria: str, cabezas: set[str]) -> bool:
    """¿Algún tramo de la ruta encabeza con una palabra del conjunto?

    Se mira la primera palabra del tramo, no el tramo entero ni una
    subcadena suelta. 'Frutas Cítricas' y 'Frutas Frescas' califican;
    'Pulpa de Frutas' no, porque su cabeza es 'pulpa'. Buscar 'frutas' como
    subcadena dejaba pasar el enlatado, y con él su foto de empaque.
    """
    from .config import CATEGORIAS_EXCLUIDAS, MODIFICADORES_PROCESADOS

    segmentos = _segmentos(categoria)
    if not segmentos:
        return False

    excluidas = {sin_tildes(c).lower() for c in CATEGORIAS_EXCLUIDAS}
    if any(s in excluidas for s in segmentos):
        return False

    cabezas_canon = {sin_tildes(c).lower() for c in cabezas}
    procesados = {sin_tildes(c).lower() for c in MODIFICADORES_PROCESADOS}

    # Manda la hoja, no el ancestro. 'Carnes/Sustitutos Cárnicos' cuelga de
    # una góndola válida pero el producto no lo es; si bastara con que algún
    # tramo calificara, el padre le abriría la puerta al hijo procesado.
    if any(p in procesados for p in _palabras(segmentos[-1])):
        return False

    for seg in segmentos:
        palabras = _palabras(seg)
        if not palabras or palabras[0] not in cabezas_canon:
            continue
        if any(p in procesados for p in palabras):
            continue
        return True
    return False


def categoria_capturable(categoria: str) -> bool:
    """¿Se guarda el precio de esta categoría?"""
    from .config import CABEZAS_CAPTURA

    return _califica(categoria, CABEZAS_CAPTURA)


def foto_elegible(categoria: str) -> bool:
    """¿Se puede espejar la foto de esta categoría?

    Solo fresco a granel, donde la imagen es el producto sobre fondo blanco.
    Grano, huevo y lácteo se capturan igual, pero su foto es el saco o el
    cartón con la marca encima: esos se quedan con la foto Creative Commons
    de assets/img/.
    """
    from .config import CABEZAS_FOTO

    return _califica(categoria, CABEZAS_FOTO)

# ------------------------------------------------------------------
# UNIDAD CANÓNICA
#
# Cada cadena escribe la misma unidad a su manera: La Sirena manda "un",
# Nacional y Fruttissimo mandan "Unidad". Son la misma cosa, pero como
# cadenas de texto distintas rompían el agrupado — el plátano, el melón y
# el coco se quedaban sin valor de referencia porque el rubro "mezclaba
# unidades" que en realidad eran una sola.
#
# Se normaliza SOLO lo que es sinónimo evidente. Litro y libra no entran
# aquí: convertir entre ellas necesita la densidad del producto y eso es
# un supuesto, no una traducción.
# ------------------------------------------------------------------
_UNIDADES = {
    "un": "Unidad", "und": "Unidad", "unid": "Unidad", "u": "Unidad",
    "unidad": "Unidad", "unidades": "Unidad", "c/u": "Unidad",
    "lb": "Libra", "lbs": "Libra", "libra": "Libra", "libras": "Libra",
    "lt": "Litro", "l": "Litro", "litro": "Litro", "litros": "Litro",
    "kg": "Kilo", "kilo": "Kilo", "kilos": "Kilo",
    "gr": "Gramo", "g": "Gramo", "gramo": "Gramo", "gramos": "Gramo",
    "oz": "Onza", "onza": "Onza", "onzas": "Onza",
}


def unidad_canonica(unidad: str | None) -> str:
    """"un" y "Unidad" son la misma unidad; como texto suelto, no."""
    if not unidad:
        return "Unidad"
    limpia = sin_tildes(unidad.strip().lower()).rstrip(".")
    return _UNIDADES.get(limpia, unidad.strip())



# ------------------------------------------------------------------
# ¿LA REFERENCIA MAYORISTA ES POR PESO?
#
# `precio_por_unidad` divide el precio del empaque entre lo que trae el
# empaque, y eso NO siempre da pesos por libra. El limón persa se cotiza en
# "Saco/600 Unidad": 4,000 entre 600 son RD$6.67 POR LIMÓN. La tarjeta lo
# enseñaba como RD$6.67/lb y lo comparaba contra RD$58.50/lb de góndola,
# que daba "+777% sobre mayorista" — el número más grande del sitio, y
# comparaba limones con libras.
#
# Devuelve el factor por el que se MULTIPLICA para pasar a libra, o None
# cuando no hay conversión honesta:
#   1.0     -> ya viene por libra
#   0.4536  -> viene por kilo. Se MULTIPLICA, no se divide: una libra pesa
#              menos que un kilo, así que la libra cuesta menos. Dividir
#              ponía la papa a RD$88/lb cuando son RD$18.11.
#   None    -> se cotiza por pieza (unidad, ciento, millar, fardo). No se
#              compara: un hueco se ve, un supuesto no.
# ------------------------------------------------------------------
_RE_LB_EMPAQUE = re.compile(r"/\s*\d+(?:[.,]\d+)?\s*(?:lb|libras?)\b", re.I)
_RE_UD_EMPAQUE = re.compile(r"/\s*\d+(?:[.,]\d+)?\s*(?:ud|und|unidad(?:es)?|u)\b", re.I)


def factor_a_libra(unidad_mayorista: str | None) -> float | None:
    if not unidad_mayorista:
        return None
    u = sin_tildes(unidad_mayorista.strip().lower())

    # Empaque contado por piezas: "Saco/600 Unidad", "Fardo/12 Ud".
    if _RE_UD_EMPAQUE.search(u):
        return None
    # Empaque pesado: "Saco/100 lb", "Huacal/20 lb", "Saco/125 lb".
    if _RE_LB_EMPAQUE.search(u):
        return 1.0
    if u in ("lb", "libra", "libras"):
        return 1.0
    # Quintal son 100 lb y `precio_por_unidad` ya dividió entre 100.
    if u == "quintal":
        return 1.0
    if u in ("kilo", "kg", "kilogramo"):
        return 0.45359237
    # Piezas sueltas.
    if u in ("ud", "und", "unidad", "unidades", "u", "ciento", "millar",
             "docena", "mata", "racimo", "litro", "lt", "galon", "carton"):
        return None
    return None
