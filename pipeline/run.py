"""Orquestador. `python -m pipeline.run [--seco] [--fuente=X] [--sembrar]`

Cada fuente corre aislada: si el Ministerio cambia una URL, MERCADOM se
captura igual — y MERCADOM es el único que no se puede pedir después.

Modos:
    --seco            no escribe nada; imprime conteos y los no mapeados
    --fuente=sirena   una sola fuente (repetible con comas)
    --sembrar         además puebla `cultivos` desde data/precios.json
    --sin-fotos       salta la descarga de imágenes
    --sin-exportar    no regenera data/*.json ni assets/js/datos.js
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys

from .comun import Resultado
from .config import FUENTES, USAR_FOTOS_RETAIL

log = logging.getLogger("kcuesta")

# Orden deliberado: primero lo que se pierde si no se captura hoy, después
# lo recuperable, y de último Firecrawl, que es lo caro y lo frágil.
ORDEN = ["mercadom", "agricultura", "sirena", "nacional", "fruttissimo", "ckan", "firecrawl"]


def _cargar_fuente(nombre: str):
    from importlib import import_module
    return import_module(f".fuentes.{nombre}", package="pipeline")


def correr(fuentes: list[str], hoy: dt.date) -> list[Resultado]:
    resultados = []
    for nombre in fuentes:
        log.info("--- %s ---", nombre)
        try:
            r = _cargar_fuente(nombre).capturar(hoy)
        except Exception as e:           # noqa: BLE001
            r = Resultado(fuente=nombre, error=f"{type(e).__name__}: {e}")
            log.error("%s reventó: %s", nombre, r.error)
        resultados.append(r)
    return resultados


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.run")
    ap.add_argument("--seco", action="store_true", help="no escribe nada")
    ap.add_argument("--fuente", default="todas", help="coma-separado, o 'todas'")
    ap.add_argument("--sembrar", action="store_true", help="puebla la tabla cultivos")
    ap.add_argument("--sin-fotos", action="store_true")
    ap.add_argument("--sin-exportar", action="store_true")
    ap.add_argument("--sin-base", action="store_true",
                    help="exporta sin Supabase (salida de emergencia y modo de prueba)")
    ap.add_argument("--fecha", default=None, help="AAAA-MM-DD, para reprocesar")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-22s  %(message)s",
        datefmt="%H:%M:%S",
    )

    hoy = dt.date.fromisoformat(args.fecha) if args.fecha else dt.date.today()
    if args.fuente == "todas":
        fuentes = ORDEN
    else:
        fuentes = [f.strip() for f in args.fuente.split(",") if f.strip()]
        desconocidas = [f for f in fuentes if f not in FUENTES]
        if desconocidas:
            ap.error(f"fuente desconocida: {desconocidas}. Conocidas: {list(FUENTES)}")

    resultados = correr(fuentes, hoy)

    # ---------------- resumen de captura ----------------
    print("\n" + "=" * 66)
    print(f"CAPTURA {hoy}")
    print("=" * 66)
    for r in resultados:
        estado = "ok  " if r.ok and r.filas else ("VACIO" if r.ok else "FALLO")
        print(f"  {estado}  {r.fuente:<14} oficiales={len(r.oficiales):<6} retail={len(r.retail):<6}"
              + (f"  {r.error}" if r.error else ""))

    oficiales = [f for r in resultados for f in r.oficiales]
    retail = [f for r in resultados for f in r.retail]
    print(f"\n  TOTAL  oficiales={len(oficiales)}  retail={len(retail)}")

    # ---------------- mapeo ----------------
    from .cargar import Mapeador

    db = None
    if not args.seco and not args.sin_base:
        from .cargar import Supabase
        db = Supabase()

    m = Mapeador(db)
    for f in oficiales:
        m.resolver(f.nombre_crudo)
    for f in retail:
        m.resolver(f.nombre)

    print("\n" + "-" * 66)
    print("MAPEO A CULTIVOS")
    print("-" * 66)
    print(m.reporte())

    if args.seco:
        print("\n(corrida en seco: no se escribió nada)")
        return 0

    # ---------------- carga ----------------
    from .cargar import (cargar_oficiales, cargar_retail, registrar_captura,
                         sembrar_cultivos)

    # El mapeador se reinicia para que el conteo de no mapeados de la carga
    # no arrastre el de la pasada de diagnóstico.
    m_carga = Mapeador(db)

    if args.sin_base:
        from .memoria import BaseEnMemoria, poblar
        db = BaseEnMemoria()
        n_of, n_pr = poblar(db, oficiales, retail, m_carga)
        print(f"\nsin base: {n_of} precios oficiales y {n_pr} productos en memoria")
    else:
        if args.sembrar:
            print(f"\ncultivos sembrados: {sembrar_cultivos(db)}")
        n_of = cargar_oficiales(db, oficiales, m_carga)
        n_pr, n_pre = cargar_retail(db, retail, m_carga)
        print(f"\nprecios_oficiales: {n_of}   productos_retail: {n_pr}   precios_retail: {n_pre}")
        for r in resultados:
            registrar_captura(db, r, len(m_carga.no_mapeados))

    # ---------------- fotos ----------------
    if args.sin_base:
        print("\nfotos: omitidas (no hay Storage sin base)")
    elif USAR_FOTOS_RETAIL and not args.sin_fotos:
        from .fotos import sincronizar
        print(f"\nfotos: {sincronizar(db)}")
    else:
        print("\nfotos: omitidas")

    # ---------------- exportación ----------------
    if not args.sin_exportar:
        from .exportar import exportar
        print(f"\n{exportar(db, hoy)}")

    fallos = [r.fuente for r in resultados if not r.ok]
    if fallos:
        print(f"\nFuentes con fallo: {', '.join(fallos)}")
    # Se devuelve 0 mientras algo se haya capturado: que Firecrawl falle no
    # puede pintar de rojo una corrida que sí guardó MERCADOM.
    return 0 if (oficiales or retail) else 1


if __name__ == "__main__":
    sys.exit(main())
