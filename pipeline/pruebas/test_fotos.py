"""Pruebas de la compuerta de fotos.

Lo que se verifica aquí es la regla acordada: se espeja fotografía de
producto limpia; lo que trae marca de agua o logo encima se deja quieto.

La heurística es la capa 2 de tres (categoría → esquinas → ojo humano). No
tiene que ser un detector perfecto; tiene que (a) dejar pasar una foto de
producto limpia y (b) levantar la mano ante un sello sobrepuesto. Si falla
en (a) perdemos fotos que sí podíamos usar; si falla en (b) lo atrapa la
revisión manual, porque nada se sirve en 'pendiente'.
"""

import io

import pytest

from pipeline.fotos import _a_webp, _sospecha_de_marca
from pipeline.normalizar import foto_elegible

Image = pytest.importorskip("PIL.Image", reason="Pillow no instalado")
ImageDraw = pytest.importorskip("PIL.ImageDraw")


def _producto_limpio(tam=(600, 600)):
    """Producto centrado sobre fondo blanco: el caso normal del fresco."""
    img = Image.new("RGB", tam, (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.ellipse([150, 150, 450, 450], fill=(90, 150, 60))
    return img


def _con_sellos(tam=(600, 600)):
    """El mismo producto con badges en las esquinas, como un '-30%' o un logo."""
    img = _producto_limpio(tam)
    d = ImageDraw.Draw(img)
    for caja in ([6, 6, 90, 60], [510, 6, 594, 60], [6, 540, 90, 594]):
        d.rectangle(caja, fill=(210, 30, 40))
        d.text((caja[0] + 10, caja[1] + 20), "-30%", fill=(255, 255, 255))
    return img


def test_producto_limpio_pasa():
    assert _sospecha_de_marca(_producto_limpio()) is None


def test_sellos_en_esquinas_se_levantan():
    motivo = _sospecha_de_marca(_con_sellos())
    assert motivo is not None
    assert "esquina" in motivo


def test_una_sola_esquina_movida_no_basta():
    """El producto asomándose a una esquina no es un sello."""
    img = _producto_limpio()
    ImageDraw.Draw(img).rectangle([6, 6, 90, 60], fill=(90, 150, 60))
    assert _sospecha_de_marca(img) is None


def test_conversion_a_webp_reduce_y_conserva():
    buf = io.BytesIO()
    _producto_limpio((1200, 1200)).save(buf, "PNG")
    original = buf.getvalue()

    webp, motivo = _a_webp(original)
    assert motivo is None
    assert len(webp) < len(original)

    salida = Image.open(io.BytesIO(webp))
    assert salida.format == "WEBP"
    assert salida.width == 480          # se reescala al ancho de tarjeta


def test_transparencia_se_aplana_en_blanco():
    """Un PNG con alfa sobre fondo oscuro se vería mal en la tarjeta."""
    img = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([50, 50, 250, 250], fill=(200, 60, 60, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")

    webp, _ = _a_webp(buf.getvalue())
    salida = Image.open(io.BytesIO(webp)).convert("RGB")
    assert salida.getpixel((5, 5)) == (255, 255, 255)


# ------------------------------------------------------------------
# Capa 1: la categoría decide antes de descargar nada
# ------------------------------------------------------------------
def test_el_empacado_no_llega_a_la_heuristica():
    """El arroz de marca se filtra por categoría, no por inspección.

    Su foto es el saco con el logo del fabricante; ahí no hay nada que
    detectar porque la marca ES el producto.
    """
    assert foto_elegible("Supermercado/Despensa/Arroz, Habichuelas y otros granos/Arroz") is False
    assert foto_elegible("Huevos y Lácteos") is False
    assert foto_elegible("Supermercado/Frutas y Vegetales/Vegetales Frescos") is True
