"""Espejado de fotos de producto a Supabase Storage.

Regla acordada con el dueño del proyecto: se espeja fotografía de producto
limpia; lo que traiga marca de agua o logo encima se deja quieto.

Se aplica en tres capas, de la más barata a la más cara:

  1. CATEGORÍA — solo fresco a granel (`foto_elegible`). El arroz o el huevo
     se capturan de precio pero su foto es el saco o el cartón con la marca
     del fabricante, así que ni se descargan.
  2. HEURÍSTICA — se miran las esquinas. Una foto de producto sobre fondo
     blanco tiene esquinas planas; un sello, un badge de descuento o un
     logo sobrepuesto meten varianza justo ahí.
  3. OJO HUMANO — nada se sirve en estado 'pendiente'. `--revisar` arma una
     hoja de contactos para aprobar el primer lote de una pasada.

La heurística no pretende ser un detector: es un filtro que adelanta
trabajo. La decisión sigue siendo del paso 3, y mientras no se apruebe, la
tarjeta usa el banco Creative Commons de assets/img/.
"""

from __future__ import annotations

import io
import logging

from .comun import sesion
from .config import BUCKET_FOTOS, SUPABASE_SERVICE_KEY, SUPABASE_URL, TIMEOUT

log = logging.getLogger("kcuesta.fotos")

ANCHO = 480
CALIDAD = 82
LOTE = 60           # fotos nuevas por corrida, para no dispararse en la Action

# Fracción de la imagen que se mira en cada esquina y desviación estándar
# por encima de la cual esa esquina se considera "con algo encima".
ESQUINA = 0.14
UMBRAL_ESQUINA = 26.0


def _sospecha_de_marca(img) -> str | None:
    """Devuelve el motivo si la imagen parece traer sello o logo, si no None."""
    from PIL import ImageStat

    gris = img.convert("L")
    an, al = gris.size
    ce, cl = max(8, int(an * ESQUINA)), max(8, int(al * ESQUINA))

    esquinas = {
        "superior izquierda": (0, 0, ce, cl),
        "superior derecha": (an - ce, 0, an, cl),
        "inferior izquierda": (0, al - cl, ce, al),
        "inferior derecha": (an - ce, al - cl, an, al),
    }
    sucias = [
        nombre for nombre, caja in esquinas.items()
        if ImageStat.Stat(gris.crop(caja)).stddev[0] > UMBRAL_ESQUINA
    ]
    # Una sola esquina movida suele ser el producto asomándose. Dos o más ya
    # es un patrón de sello o banda superpuesta.
    if len(sucias) >= 2:
        return f"posible marca o sello en {len(sucias)} esquinas ({', '.join(sucias)})"
    return None


def _a_webp(bruto: bytes) -> tuple[bytes, str | None]:
    from PIL import Image

    img = Image.open(io.BytesIO(bruto))
    img.load()
    motivo = _sospecha_de_marca(img)

    if img.mode in ("RGBA", "LA", "P"):
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        img = img.convert("RGBA")
        fondo.paste(img, mask=img.split()[-1])
        img = fondo
    else:
        img = img.convert("RGB")

    if img.width > ANCHO:
        alto = round(img.height * ANCHO / img.width)
        img = img.resize((ANCHO, alto), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=CALIDAD, method=4)
    return buf.getvalue(), motivo


def _subir(s, ruta: str, contenido: bytes) -> str:
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_FOTOS}/{ruta}"
    resp = s.post(
        url, data=contenido,
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "image/webp",
            "x-upsert": "true",
        },
        timeout=TIMEOUT,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"storage {resp.status_code}: {resp.text[:200]}")
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_FOTOS}/{ruta}"


def sincronizar(db, lote: int = LOTE) -> str:
    """Descarga las fotos pendientes que aún no se han espejado."""
    pendientes = db.seleccionar(
        "productos_retail",
        select="id,cadena_id,sku_externo,foto_origen_url,categoria_externa",
        foto_estado="eq.pendiente",
        foto_url="is.null",
        foto_origen_url="not.is.null",
        limit=str(lote),
    )
    if not pendientes:
        return "nada pendiente de espejar"

    s = sesion()
    subidas = rechazadas = fallidas = 0

    for p in pendientes:
        try:
            resp = s.get(p["foto_origen_url"], timeout=TIMEOUT)
            resp.raise_for_status()
            webp, motivo = _a_webp(resp.content)
        except Exception as e:           # noqa: BLE001
            log.warning("foto %s: %s", p["sku_externo"], e)
            fallidas += 1
            continue

        if motivo:
            db.upsert("productos_retail", [{
                "cadena_id": p["cadena_id"], "sku_externo": p["sku_externo"],
                "foto_estado": "rechazada", "foto_motivo": motivo,
            }], en_conflicto="cadena_id,sku_externo")
            rechazadas += 1
            continue

        ruta = f"{p['cadena_id']}/{p['sku_externo']}.webp"
        try:
            publica = _subir(s, ruta, webp)
        except Exception as e:           # noqa: BLE001
            log.warning("subida %s: %s", ruta, e)
            fallidas += 1
            continue

        # Sigue en 'pendiente' a propósito: espejada pero sin aprobar todavía.
        db.upsert("productos_retail", [{
            "cadena_id": p["cadena_id"], "sku_externo": p["sku_externo"],
            "foto_url": publica,
        }], en_conflicto="cadena_id,sku_externo")
        subidas += 1

    return (f"{subidas} espejadas (siguen pendientes de aprobar), "
            f"{rechazadas} rechazadas por sospecha de marca, {fallidas} fallidas")


def hoja_de_revision(db, salida: str = "revision-fotos.html") -> str:
    """Arma una hoja de contactos para aprobar o rechazar en una pasada."""
    filas = db.seleccionar(
        "productos_retail",
        select="id,cadena_id,sku_externo,nombre_externo,foto_url,categoria_externa",
        foto_estado="eq.pendiente",
        foto_url="not.is.null",
        limit="500",
    )
    tarjetas = "\n".join(
        f'<figure><img src="{f["foto_url"]}" loading="lazy" alt="">'
        f'<figcaption><b>{f["cadena_id"]}</b> · {f["sku_externo"]}<br>'
        f'{f["nombre_externo"]}</figcaption></figure>'
        for f in filas
    )
    html = f"""<!doctype html><meta charset="utf-8">
<title>Revisión de fotos — {len(filas)} pendientes</title>
<style>
 body{{font:14px/1.4 system-ui;margin:24px;background:#FBFAF6;color:#1a1a1a}}
 h1{{font-size:18px}}
 .rejilla{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:16px}}
 figure{{margin:0;background:#fff;border:1px solid #e5e2d9;border-radius:8px;padding:8px}}
 img{{width:100%;aspect-ratio:1;object-fit:contain;background:#fff}}
 figcaption{{font-size:11px;color:#555;margin-top:6px}}
</style>
<h1>{len(filas)} fotos espejadas, pendientes de aprobar</h1>
<p>Busca marca de agua o logo sobrepuesto. Lo que tenga, se rechaza:
 la tarjeta cae sola a la foto Creative Commons.</p>
<div class="rejilla">{tarjetas}</div>
"""
    with open(salida, "w", encoding="utf-8") as f:
        f.write(html)
    return f"{salida} escrito con {len(filas)} fotos"


if __name__ == "__main__":
    import argparse

    from .cargar import Supabase

    ap = argparse.ArgumentParser(prog="pipeline.fotos")
    ap.add_argument("--revisar", action="store_true", help="arma la hoja de contactos")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    db = Supabase()
    print(hoja_de_revision(db) if args.revisar else sincronizar(db))
