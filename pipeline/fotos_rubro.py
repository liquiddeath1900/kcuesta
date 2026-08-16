"""Una foto por rubro, espejada de la góndola.

Por qué esta y no Wikimedia: la cadena fotografía el producto limpio, de
frente, sobre fondo blanco, porque necesita vendérselo a alguien. Es
exactamente lo que la tarjeta necesita. Commons, en cambio, tiene sus
categorías curadas para botánica — en una tanda de 24 devolvió un caldero
vacío para el arroz, una hoja enferma para la habichuela, corteza de árbol
para el mango y una lámina escaneada para el melón.

Se guarda en el repo, no en Supabase Storage. Son 44 imágenes de ~20 KB que
GitHub Pages sirve sin pestañear, quedan versionadas junto al código que las
usa, y no dependen de que la base esté levantada. Cuando haya productores
subiendo sus propias fotos, esas sí van a Storage: son de ellos y cambian.

Regla de siempre, la que puso el dueño del proyecto: se espeja fotografía de
producto limpia; lo que traiga marca de agua o logo encima se deja quieto.
Aquí se aplica igual — categoría de fresco a granel primero, heurística de
esquinas después.
"""

from __future__ import annotations

import json
import logging

from .comun import sesion
from .config import DATOS, RAIZ, TIMEOUT
from .normalizar import foto_elegible

log = logging.getLogger("kcuesta.fotos_rubro")

DESTINO = RAIZ / "assets" / "img" / "rubros"
CREDITOS = DESTINO / "CREDITOS.json"


def sincronizar(solo_faltantes: bool = True) -> str:
    ruta = DATOS / "ofertas.json"
    if not ruta.exists():
        return "no hay data/ofertas.json todavía; corre el pipeline primero"

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    rubros = datos.get("rubros", [])
    cadenas = datos.get("cadenas", {})
    if not rubros:
        return "ofertas.json no trae rubros"

    DESTINO.mkdir(parents=True, exist_ok=True)
    creditos = json.loads(CREDITOS.read_text()) if CREDITOS.exists() else {}
    s = sesion()

    from .fotos import _a_webp

    bajadas = rechazadas = saltadas = fallidas = 0

    for r in rubros:
        cid = r["cultivo"]
        destino = DESTINO / f"{cid}.webp"
        if solo_faltantes and destino.exists() and cid in creditos:
            saltadas += 1
            continue

        # Orden de preferencia: primero el fresco a granel, donde la foto es
        # el producto pelado sobre blanco; si el rubro no tiene ninguna
        # —arroz, habichuela, leche solo se venden empacados— se acepta la
        # del empaque.
        #
        # La regla del dueño es sobre la MARCA DE AGUA de la cadena, no
        # sobre el envase del fabricante: un saco de arroz Líder no lleva
        # encima el logo de Nacional. Excluir todo lo empacado dejaba ocho
        # rubros sin foto y los mandaba de vuelta al banco repetido. Lo que
        # decide sigue siendo la heurística de esquinas de abajo.
        candidatas = [o for o in r["ofertas"] if o.get("foto_origen")]
        frescas = [o for o in candidatas
                   if foto_elegible(o.get("categoria_externa") or "")]
        elegida = next(iter(frescas or candidatas), None)

        if not elegida:
            saltadas += 1
            continue

        try:
            bruto = s.get(elegida["foto_origen"], timeout=TIMEOUT).content
            webp, motivo = _a_webp(bruto)
        except Exception as e:            # noqa: BLE001
            log.warning("%s: %s", cid, e)
            fallidas += 1
            continue

        if motivo:
            log.info("%-22s rechazada: %s", cid, motivo)
            rechazadas += 1
            continue

        destino.write_bytes(webp)
        creditos[cid] = {
            "archivo": f"assets/img/rubros/{cid}.webp",
            "cadena": cadenas.get(elegida["cadena"], {}).get("nombre", elegida["cadena"]),
            "producto": elegida["titulo"],
            "url_producto": elegida.get("url"),
            "origen": elegida["foto_origen"],
        }
        bajadas += 1
        log.info("%-22s %s", cid, elegida["titulo"][:60])

    CREDITOS.write_text(json.dumps(creditos, ensure_ascii=False, indent=2), encoding="utf-8")
    return (f"{bajadas} espejadas, {rechazadas} rechazadas por sospecha de marca, "
            f"{saltadas} sin foto elegible, {fallidas} fallidas")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(prog="pipeline.fotos_rubro")
    ap.add_argument("--todos", action="store_true")
    a = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(sincronizar(solo_faltantes=not a.todos))
