"""Rutas, credenciales y perillas del pipeline."""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "archivo"
DATOS = RAIZ / "data"
ASSETS_JS = RAIZ / "assets" / "js"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://sjoohrwxsirdcxtpexwk.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")

# Interruptor de las fotos de supermercado. En false, las tarjetas usan el
# banco Creative Commons de assets/img/ y no se descarga ni una imagen.
USAR_FOTOS_RETAIL = os.environ.get("USAR_FOTOS_RETAIL", "true").lower() != "false"

BUCKET_FOTOS = "retail-fotos"

# Se navega con user agent de navegador porque varios de estos sitios
# devuelven 403 a un cliente sin identificar. No es evasión: es que el
# default de requests está en más de una lista negra por defecto.
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
TIMEOUT = 45

# Dos preguntas distintas que conviene no mezclar:
#
#   1. ¿Se captura el precio? Sí para todo lo agropecuario, incluido el
#      arroz y la habichuela empacados: el precio de góndola del arroz
#      sirve igual aunque el saco lleve marca.
#   2. ¿Se espeja la foto? Solo cuando la imagen es el producto y no el
#      empaque. El arroz de marca tiene el logo del fabricante EN la foto,
#      así que se captura su precio y su foto se descarta.
#
# CATEGORIAS_CAPTURA responde a la primera. CATEGORIAS_FOTO, a la segunda.
# Las tres cadenas nombran sus categorías de forma incompatible entre sí:
#
#   Sirena       'Supermercado/Frutas y Vegetales/Vegetales Frescos'
#   Fruttissimo  'Frutas Frescas', 'Vegetales Importados', 'Víveres Frescos'
#   Nacional     'Frutas Cítricas', 'Frutas Tropicales y Exóticas'
#
# Por eso no se comparan nombres completos sino la PALABRA CABEZA del tramo.
# 'frutas' encabeza los tres. Un listado exacto habría que reescribirlo cada
# vez que una cadena renombra una góndola.
CABEZAS_CAPTURA = {
    "frutas", "fruta", "vegetales", "vegetal", "verduras", "hortalizas",
    "viveres", "provisiones", "tuberculos", "raices",
    "carnes", "carne", "pescados", "pescado", "mariscos",
    "huevos", "lacteos", "leche",
    "granos", "arroz", "habichuelas", "legumbres",
}
# 'cereales' y 'quesos' se quedaron fuera tras ver la captura real: traían
# 120 granolas de Nacional y toda la quesera. Ninguno es cultivo del
# catálogo, así que solo engordaban la lista de no mapeados.

# De esas, las que llegan a granel y se fotografían sobre fondo blanco.
# Grano, huevo y lácteo se capturan pero NO se les espeja la foto: ahí la
# imagen es el saco o el cartón, con la marca del fabricante encima.
CABEZAS_FOTO = {
    "frutas", "fruta", "vegetales", "vegetal", "verduras", "hortalizas",
    "viveres", "provisiones", "tuberculos", "raices",
    "carnes", "carne", "pescados", "pescado", "mariscos",
}

# Palabras que, aparezcan donde aparezcan en el tramo, lo descalifican.
# 'Frutas Congeladas' y 'Pulpa de Frutas' encabezan con 'frutas' pero son
# producto procesado de marca: ni su precio es comparable contra una finca
# ni su foto es del producto.
MODIFICADORES_PROCESADOS = {
    "congelado", "congelados", "congeladas", "congelada",
    "seco", "secos", "seca", "secas", "deshidratado", "deshidratados",
    "deshidratadas", "conserva", "conservas", "enlatado", "enlatados",
    "pulpa", "jugo", "jugos", "zumo", "zumos", "smoothies", "smoothie",
    "sustitutos", "aceitunas", "encurtidos", "mermelada", "mermeladas",
}

# Góndolas completas que nunca entran.
CATEGORIAS_EXCLUIDAS = {
    "congelados", "bebidas", "cervezas", "limpieza", "mascotas",
    "galletas", "dulces", "panaderia", "reposteria", "condimentos",
    "listo para comer", "cuidado personal", "bebe", "navidad",
    "dieta y nutricion", "proteinas y suplementos",
}
# 'Despensa' NO va aquí a propósito: en Sirena el arroz cuelga de
# 'Despensa/Arroz, Habichuelas y otros granos/Arroz' y excluir la góndola
# entera se llevaba por delante los granos. Como 'despensa' tampoco es
# palabra cabeza, la góndola suelta no califica igual.

FUENTES = (
    "ckan",
    "agricultura",
    "mercadom",
    "sirena",
    "nacional",
    "fruttissimo",
    "firecrawl",
)
