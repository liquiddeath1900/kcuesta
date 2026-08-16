"""Tipos compartidos, HTTP y archivo de crudos."""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .config import ARCHIVO, TIMEOUT, UA

log = logging.getLogger("kcuesta")


@dataclass
class FilaOficial:
    """Un precio de la serie oficial, con grano de cultivo."""
    nombre_crudo: str
    fecha: dt.date
    nivel: str            # mayorista | minorista | supermercado | colmado
    unidad: str
    precio: float
    fuente: str
    fuente_url: str
    mercado: str | None = None   # 'Mercado Nuevo', 'CONAPROPE', ...


@dataclass
class FilaRetail:
    """Un precio de supermercado, con grano de SKU."""
    cadena_id: str
    sku: str
    nombre: str
    precio: float
    fecha: dt.date
    categoria: str | None = None
    unidad: str | None = None
    precio_lista: float | None = None
    disponible: bool = True
    url_producto: str | None = None
    foto_origen_url: str | None = None


@dataclass
class Resultado:
    """Lo que devuelve cada fetcher. Un fallo es un resultado, no una excepción.

    El pipeline corre siete fuentes; que el Ministerio cambie una URL no
    puede impedir que MERCADOM se capture ese día, porque MERCADOM es el
    que no se puede recuperar después.
    """
    fuente: str
    oficiales: list[FilaOficial] = field(default_factory=list)
    retail: list[FilaRetail] = field(default_factory=list)
    artefacto: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def filas(self) -> int:
        return len(self.oficiales) + len(self.retail)


def sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "es-DO,es;q=0.9"})
    # El descubrimiento del informe sondea hasta doce URLs a la vez; con el
    # pool por defecto (10) requests descarta y reabre conexiones sin parar.
    adaptador = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=16)
    s.mount("https://", adaptador)
    s.mount("http://", adaptador)
    return s


def guardar_crudo(nombre: str, contenido: bytes, fecha: dt.date | None = None) -> str:
    """Deja el archivo original en archivo/YYYY/MM/DD/ y devuelve su ruta.

    Se guarda ANTES de parsear. Si el parser se rompe porque la fuente
    cambió de formato, el dato del día sigue en disco y se puede reprocesar;
    si solo se guardara lo parseado, un cambio de formato borraría el día.
    """
    fecha = fecha or dt.date.today()
    carpeta = ARCHIVO / f"{fecha:%Y/%m/%d}"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre
    destino.write_bytes(contenido)
    rel = destino.relative_to(Path(ARCHIVO).parent)
    log.info("crudo guardado: %s (%d KB)", rel, len(contenido) // 1024)
    return str(rel)


def pdf_a_texto(ruta: Path | str) -> str:
    """Extrae texto conservando columnas. Requiere poppler (pdftotext)."""
    import subprocess

    r = subprocess.run(
        ["pdftotext", "-layout", str(ruta), "-"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"pdftotext falló: {r.stderr.strip()[:200]}")
    return r.stdout


MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
