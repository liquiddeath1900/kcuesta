"""Una foto propia por cultivo, desde Wikimedia Commons.

El problema que resuelve: el banco de assets/img/ tiene 16 fotos para 81
cultivos, así que el mapeo por categoría repetía la misma imagen sin parar
—`habichuela.jpg` salía en 47 tarjetas y `aji.jpg` en 31—. Una página de
precios donde todo se ve igual no se puede escanear.

Se busca por BINOMIO CIENTÍFICO, no por nombre común. CREDITOS.md ya avisa
por qué: buscar "piña" en Commons devolvió una carretera y "plátano"
devolvió *Plantago*, que es una maleza. `Ananas comosus` no tiene ese
problema. Aun así la búsqueda por texto sigue siendo aproximada, así que:

  * se prefiere la imagen de la CATEGORÍA de la especie, no la del buscador
  * se descarta lo que no sea foto (mapas, diagramas, herbarios, sellos)
  * se guarda autor y licencia de cada archivo para el crédito
  * y queda un paso de revisión visual, porque el criterio de CREDITOS.md
    es "el producto de cerca, no el paisaje" y eso no lo decide una API

Uso:
    python -m pipeline.imagenes --faltantes     # solo los que no tienen
    python -m pipeline.imagenes --todos
    python -m pipeline.imagenes --hoja          # hoja de contactos para revisar
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .catalogo import cultivos
from .comun import sesion
from .config import RAIZ, TIMEOUT
from .normalizar import sin_tildes

log = logging.getLogger("kcuesta.imagenes")

API = "https://commons.wikimedia.org/w/api.php"
DESTINO = RAIZ / "assets" / "img" / "cultivos"
CREDITOS = DESTINO / "CREDITOS.json"
ANCHO = 640

# Binomio + término de respaldo por cultivo. La variedad dominicana rara vez
# tiene foto propia en Commons, así que se apunta a la especie: un ají
# cubanela y un ají morrón son ambos Capsicum annuum, pero al menos la foto
# es de un ají y no de otra cosa.
ESPECIES = {
    "platano-barahonero":  ("Musa × paradisiaca", "plantain fruit"),
    "platano-cibao":       ("Musa × paradisiaca", "plantain bunch"),
    "platano-fhia20":      ("Musa × paradisiaca", "plantain green"),
    "platano-verde":       ("Musa × paradisiaca", "green plantain"),
    "platano-macho":       ("Musa × paradisiaca", "plantain macho"),
    "platano-enano":       ("Musa × paradisiaca", "dwarf plantain"),
    "platano-maduro":      ("Musa × paradisiaca", "ripe plantain"),
    "guineo-verde":        ("Musa acuminata", "banana green"),
    "yuca-bilin":          ("Manihot esculenta", "cassava root"),
    "batata-tifey":        ("Ipomoea batatas", "sweet potato root"),
    "name-mina":           ("Dioscorea rotundata", "yam tuber"),
    "name-jamaiquino":     ("Dioscorea cayenensis", "yellow yam"),
    "yautia-blanca":       ("Xanthosoma sagittifolium", "malanga corm"),
    "yautia-amarilla":     ("Xanthosoma sagittifolium", "yautia corm"),
    "yautia-coco":         ("Colocasia esculenta", "taro corm"),
    "papa":                ("Solanum tuberosum", "potato tubers"),

    "aji-cubanela":        ("Capsicum annuum", "cubanelle pepper"),
    "aji-gustoso":         ("Capsicum chinense", "seasoning pepper"),
    "aji-morron":          ("Capsicum annuum", "bell pepper red"),
    "aji-cachucha":        ("Capsicum chinense", "cachucha pepper"),
    "tomate-ensalada":     ("Solanum lycopersicum", "tomato fruit"),
    "tomate-bugalu":       ("Solanum lycopersicum", "tomatoes crate"),
    "cebolla-roja":        ("Allium cepa", "red onion bulbs"),
    "cebolla-amarilla":    ("Allium cepa", "yellow onion bulbs"),
    "ajo-importado":       ("Allium sativum", "garlic bulbs"),
    "zanahoria":           ("Daucus carota", "carrots harvested"),
    "berenjena":           ("Solanum melongena", "eggplant fruit"),
    "auyama":              ("Cucurbita moschata", "calabaza squash"),
    "lechuga":             ("Lactuca sativa", "lettuce head"),
    "molondron":           ("Abelmoschus esculentus", "okra pods"),
    "pepino":              ("Cucumis sativus", "cucumber fruit"),
    "remolacha":           ("Beta vulgaris", "beetroot harvested"),
    "rabano":              ("Raphanus sativus", "radish roots"),
    "coliflor":            ("Brassica oleracea var. botrytis", "cauliflower head"),
    "brocoli":             ("Brassica oleracea var. italica", "broccoli head"),
    "tayota":              ("Sechium edule", "chayote fruit"),
    "vainita":             ("Phaseolus vulgaris", "green beans pods"),
    "apio":                ("Apium graveolens", "celery stalks"),

    "aguacate-criollo":    ("Persea americana", "avocado fruit"),
    "aguacate-popenoe":    ("Persea americana", "avocado green"),
    "aguacate-benny":      ("Persea americana", "avocado tree fruit"),
    "aguacate-carla":      ("Persea americana", "avocado halved"),
    "aguacate-semil":      ("Persea americana", "avocados market"),
    "lechosa":             ("Carica papaya", "papaya fruit"),
    "lechosa-maradol":     ("Carica papaya", "papaya maradol"),
    "pina-md2":            ("Ananas comosus", "pineapple fruit"),
    "chinola":             ("Passiflora edulis", "passion fruit"),
    "limon-persa":         ("Citrus × latifolia", "persian lime"),
    "limon-criollo":       ("Citrus aurantiifolia", "key lime"),
    "naranja-agria":       ("Citrus × aurantium", "bitter orange fruit"),
    "naranja-dulce":       ("Citrus × sinensis", "sweet orange fruit"),
    "coco-seco":           ("Cocos nucifera", "coconut fruit"),
    "melon-cantaloupe":    ("Cucumis melo", "cantaloupe melon"),
    "sandia":              ("Citrullus lanatus", "watermelon fruit"),
    "zapote":              ("Pouteria sapota", "mamey sapote fruit"),
    "mango-keitt":         ("Mangifera indica", "mango fruit"),
    "mango-banilejo":      ("Mangifera indica", "mangoes market"),
    "mango-gota-oro":      ("Mangifera indica", "mango yellow"),
    "mango-tommy":         ("Mangifera indica", "mango tommy atkins"),

    # Grano y leche van SIN binomio, a propósito. La categoría botánica de
    # Commons devolvió una mata de arroz en el campo, un caldero vacío, una
    # semilla suelta, una hoja enferma y un gorgojo sobre tierra. Para un
    # producto de despensa la búsqueda por término de producto acierta mucho
    # más que la taxonomía.
    "habichuela-roja":     (None, "red kidney beans dry pile"),
    "habichuela-negra":    (None, "black beans dry pile"),
    "habichuela-blanca":   (None, "white navy beans dry"),
    "habichuela-pinta":    (None, "pinto beans dry"),
    "habichuela-yacomelo": (None, "red beans dried heap"),
    "guandul-verde":       ("Cajanus cajan", "pigeon pea pods"),
    "arroz-selecto":       (None, "white rice grains heap"),
    "arroz-super-selecto": (None, "long grain white rice"),
    "arroz-superior":      (None, "polished rice grains bowl"),
    "maiz-amarillo":       (None, "yellow maize kernels heap"),

    "leche-liquida":       (None, "milk bottle glass white"),
    "res-bola":            (None, "beef cuts butcher"),
    "res-cadera":          (None, "beef rump steak"),
    "res-pecho":           (None, "beef brisket"),
    "res-roti":            (None, "beef roast raw"),
    "res-banda":           (None, "beef carcass"),
    "cerdo-chuleta":       (None, "pork chop raw"),
    "cerdo-chuleta-ahumada": (None, "smoked pork chop"),
    "cerdo-pierna":        (None, "pork leg raw"),
    "cerdo-guisar":        (None, "pork stew meat"),
    "pollo-procesado":     (None, "raw chicken meat"),
    "pollo-vivo":          (None, "live chicken"),
    "huevos":              (None, "chicken eggs"),
    "leche-liquida":       (None, "milk glass bottle"),
}

# Lo que no sirve aunque el buscador lo devuelva.
BASURA = re.compile(
    r"(map|diagram|chart|logo|coat.of.arms|stamp|herbari|illustration|drawing|"
    r"botanical|plate|1[6-9]\d\d|distribution|range|flag|icon|svg)",
    re.I,
)
EXT_OK = (".jpg", ".jpeg", ".png", ".webp")


# Wikimedia exige un User-Agent que identifique al cliente y dé un contacto;
# con el genérico de requests devuelve 429 a las pocas llamadas.
UA_COMMONS = "KcuestaBot/1.0 (https://kcuesta.com; liquiddeath1900@gmail.com) requests"
PAUSA = 1.1          # segundos entre llamadas, por cortesía y por el 429


def _pedir(s, **params):
    import time

    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    for intento in range(4):
        r = s.get(API, params=params, timeout=TIMEOUT,
                  headers={"User-Agent": UA_COMMONS})
        if r.status_code == 429:
            espera = PAUSA * (2 ** intento)
            log.debug("429 de Commons, esperando %.1fs", espera)
            time.sleep(espera)
            continue
        r.raise_for_status()
        time.sleep(PAUSA)
        return r.json()
    raise RuntimeError("Commons sigue devolviendo 429 tras 4 intentos")


# Se quiere el producto, no la mata. CREDITOS.md lo dice explícito: "la foto
# principal debe ser el producto de cerca, no el paisaje".
PREMIA = re.compile(r"(fruit|fruto|harvest|cosech|market|mercado|crate|basket|"
                    r"seeds?|grain|bulb|root|tuber|pods?|closeup|close.up)", re.I)
CASTIGA = re.compile(r"(tree|arbol|árbol|flower|flor|leaf|leaves|hoja|plant|planta|"
                     r"field|campo|orchard|garden|jardin|seedling|blossom|bark|"
                     r"landscape|dog|husky|people|man|woman)", re.I)


def _puntuar(titulo: str, respaldo: str, de_categoria: bool) -> int:
    """Ordena candidatos: primero lo que se parece a un producto de cerca.

    Los pesos se calibraron mirando la primera tanda. Con la categoría en
    +12 y el castigo en −9, los cuatro aguacates salieron con la MISMA foto
    de un árbol lejano: pertenecer a la categoría bastaba para ganar. El
    castigo por 'tree/plant/field' ahora pesa más que cualquier bono, que es
    lo que pide CREDITOS.md — "el producto de cerca, no el paisaje".
    """
    t = sin_tildes(titulo).lower()
    puntos = 5 if de_categoria else 0
    puntos += sum(4 for p in sin_tildes(respaldo).lower().split()
                  if len(p) > 3 and p in t)
    if PREMIA.search(t):
        puntos += 10
    if CASTIGA.search(t):
        puntos -= 25          # descalifica de hecho, salvo que no haya nada más
    return puntos


def _candidatos(s, binomio: str | None, respaldo: str) -> list[str]:
    """Títulos de archivo candidatos, mejor primero."""
    crudos: list[tuple[str, bool]] = []

    # 1) La categoría de la especie es lo más confiable que da Commons:
    #    la curan personas, no un índice de texto.
    if binomio:
        try:
            d = _pedir(s, action="query", list="categorymembers",
                       cmtitle=f"Category:{binomio}", cmtype="file", cmlimit="40")
            crudos += [(m["title"], True) for m in d.get("query", {}).get("categorymembers", [])]
        except Exception as e:                       # noqa: BLE001
            log.debug("sin categoría para %s: %s", binomio, e)

    # 2) Búsqueda por texto, como respaldo. Trae ruido —la búsqueda de
    #    aguacate devolvió una foto de perros bajo un árbol de aguacate—,
    #    así que va con menos peso y pasa por el puntaje igual.
    for consulta in filter(None, [respaldo, binomio]):
        try:
            d = _pedir(s, action="query", list="search",
                       srsearch=f"{consulta} filetype:bitmap",
                       srnamespace="6", srlimit="25")
            crudos += [(m["title"], False) for m in d.get("query", {}).get("search", [])]
        except Exception as e:                       # noqa: BLE001
            log.debug("búsqueda falló para %s: %s", consulta, e)

    vistos, puntuados = set(), []
    for t, de_cat in crudos:
        if t in vistos:
            continue
        vistos.add(t)
        if BASURA.search(t) or not t.lower().endswith(EXT_OK):
            continue
        puntuados.append((_puntuar(t, respaldo, de_cat), t))

    puntuados.sort(key=lambda x: -x[0])
    return [t for _, t in puntuados]


def _info(s, titulos: list[str]) -> list[dict]:
    """Metadatos (url, licencia, autor) de un lote de archivos."""
    salida = []
    for i in range(0, len(titulos), 20):
        d = _pedir(s, action="query", titles="|".join(titulos[i:i + 20]),
                   prop="imageinfo", iiprop="url|extmetadata|size",
                   iiurlwidth=str(ANCHO))
        for p in d.get("query", {}).get("pages", []):
            ii = (p.get("imageinfo") or [{}])[0]
            if not ii.get("thumburl"):
                continue
            meta = ii.get("extmetadata", {})
            lic = (meta.get("LicenseShortName", {}) or {}).get("value", "")
            # Solo licencias que permiten uso comercial, igual que el banco
            # que ya está en el repo.
            if not re.search(r"CC|Public domain|CC0", lic, re.I) or "NC" in lic.upper():
                continue
            if (ii.get("width") or 0) < 400:
                continue
            salida.append({
                "titulo": p["title"],
                "thumb": ii["thumburl"],
                "pagina": ii.get("descriptionurl", ""),
                "licencia": lic,
                "autor": re.sub(r"<[^>]+>", "", (meta.get("Artist", {}) or {}).get("value", ""))[:120].strip(),
            })

    # La API devuelve las páginas en su propio orden y eso tiraría a la
    # basura el puntaje. Se restituye el orden con el que se pidieron.
    orden = {t: i for i, t in enumerate(titulos)}
    salida.sort(key=lambda x: orden.get(x["titulo"], 999))
    return salida


def _guardar(s, url: str, destino: Path) -> bool:
    from .fotos import _a_webp

    try:
        bruto = s.get(url, timeout=TIMEOUT).content
        webp, _ = _a_webp(bruto)          # no se aplica la heurística de marca:
        destino.write_bytes(webp)         # aquí la licencia ya es libre
        return True
    except Exception as e:                # noqa: BLE001
        log.warning("no se pudo guardar %s: %s", destino.name, e)
        return False


def sincronizar(solo_faltantes: bool = True, solo: list[str] | None = None) -> str:
    DESTINO.mkdir(parents=True, exist_ok=True)
    creditos = json.loads(CREDITOS.read_text()) if CREDITOS.exists() else {}
    s = sesion()

    ids = [c["id"] for c in cultivos() if c["id"] in ESPECIES]
    if solo:
        ids = [i for i in ids if i in solo]
    bajadas = fallidas = 0

    # Ningún archivo de Commons se usa dos veces. Sin esto, los cuatro
    # aguacates y los dos ajíes salían con la misma foto: comparten especie,
    # así que comparten el primer candidato. Repetir la imagen es
    # justamente el problema que este módulo vino a resolver.
    usados = {v.get("titulo") for v in creditos.values() if v.get("titulo")}

    for cid in ids:
        destino = DESTINO / f"{cid}.webp"
        if solo_faltantes and destino.exists() and cid in creditos:
            continue

        binomio, respaldo = ESPECIES[cid]
        titulos = [t for t in _candidatos(s, binomio, respaldo) if t not in usados]
        if not titulos:
            log.warning("sin candidatos: %s", cid)
            fallidas += 1
            continue

        try:
            elegido = next(iter(_info(s, titulos[:12])), None)
        except Exception as e:            # noqa: BLE001
            # Un 429 persistente en un cultivo no puede tumbar los otros
            # sesenta. Se anota y se sigue; la próxima corrida lo reintenta
            # porque --faltantes solo mira los que no tienen archivo.
            log.warning("%s: %s", cid, e)
            fallidas += 1
            continue
        if not elegido:
            log.warning("sin archivo con licencia libre: %s", cid)
            fallidas += 1
            continue

        if _guardar(s, elegido["thumb"], destino):
            usados.add(elegido["titulo"])
            creditos[cid] = {
                "archivo": f"assets/img/cultivos/{cid}.webp",
                "especie": binomio,
                "titulo": elegido["titulo"],
                "pagina": elegido["pagina"],
                "licencia": elegido["licencia"],
                "autor": elegido["autor"],
                "revisado": False,      # nadie lo ha mirado todavía
            }
            bajadas += 1
            log.info("%-22s %s", cid, elegido["titulo"][:70])
        else:
            fallidas += 1

    CREDITOS.write_text(json.dumps(creditos, ensure_ascii=False, indent=2), encoding="utf-8")
    sin_revisar = sum(1 for v in creditos.values() if not v.get("revisado"))
    return (f"{bajadas} bajadas, {fallidas} sin resolver, "
            f"{len(creditos)} en total, {sin_revisar} sin revisar a ojo")


def hoja(salida: Path | None = None) -> str:
    """Hoja de contactos para revisar a ojo, como manda CREDITOS.md."""
    salida = salida or (RAIZ / "revision-cultivos.html")
    creditos = json.loads(CREDITOS.read_text()) if CREDITOS.exists() else {}
    nombres = {c["id"]: c["nombre"] for c in cultivos()}

    tarjetas = "\n".join(
        f'<figure><img src="{v["archivo"]}" loading="lazy" alt="">'
        f'<figcaption><b>{nombres.get(k, k)}</b><br><i>{v.get("especie") or "—"}</i><br>'
        f'<a href="{v["pagina"]}" target="_blank">{v["licencia"]}</a></figcaption></figure>'
        for k, v in sorted(creditos.items())
    )
    html = f"""<!doctype html><meta charset="utf-8">
<title>Revisión de fotos de cultivo</title>
<style>
 body{{font:14px/1.4 system-ui;margin:24px;background:#FBFAF6;color:#1a1a1a}}
 .rejilla{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px}}
 figure{{margin:0;background:#fff;border:1px solid #e5e2d9;border-radius:8px;padding:8px}}
 img{{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:4px}}
 figcaption{{font-size:11px;color:#555;margin-top:6px}}
</style>
<h1>{len(creditos)} fotos de cultivo</h1>
<p>Criterio de CREDITOS.md: <b>el producto de cerca, no el paisaje</b>.
 Lo que salga un mapa, una flor sin fruto o un campo lejano, se reemplaza.</p>
<div class="rejilla">{tarjetas}</div>
"""
    salida.write_text(html, encoding="utf-8")
    return f"{salida} con {len(creditos)} fotos"


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(prog="pipeline.imagenes")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--faltantes", action="store_true")
    ap.add_argument("--hoja", action="store_true")
    ap.add_argument("--solo", default="", help="ids separados por coma")
    a = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    solo = [x.strip() for x in a.solo.split(",") if x.strip()] or None
    print(hoja() if a.hoja
          else sincronizar(solo_faltantes=not a.todos, solo=solo))
