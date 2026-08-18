"""Pruebas del valor de referencia y de la unidad canónica.

Las dos piezas que se estrenaron el día que la tarjeta dejó de encabezar el
precio más barato y pasó a encabezar cuánto vale el rubro. Los casos son
datos reales de la captura del 16 de agosto 2026.

    python -m pytest pipeline/pruebas -q
"""

import pytest

from pipeline.exportar import resumen_valor
from pipeline.normalizar import unidad_canonica


# ------------------------------------------------------------------
# unidad_canonica
# ------------------------------------------------------------------

@pytest.mark.parametrize("entrada,esperado", [
    # El caso que rompía el agrupado: La Sirena manda "un", Nacional y
    # Fruttissimo mandan "Unidad". Como texto suelto son distintos, y el
    # plátano, el melón y el coco se quedaban sin valor de referencia
    # porque el rubro parecía "mezclar unidades".
    ("un", "Unidad"),
    ("Unidad", "Unidad"),
    ("UND", "Unidad"),
    ("und.", "Unidad"),
    ("unidades", "Unidad"),
    ("lb", "Libra"),
    ("Libras", "Libra"),
    ("lt", "Litro"),
    (None, "Unidad"),
    ("", "Unidad"),
])
def test_unidad_canonica_junta_sinonimos(entrada, esperado):
    assert unidad_canonica(entrada) == esperado


def test_unidad_canonica_no_inventa_conversiones():
    """Litro y libra NO son sinónimos: convertir necesita la densidad del
    producto, que es un supuesto y no una traducción."""
    assert unidad_canonica("Litro") == "Litro"
    assert unidad_canonica("Libra") == "Libra"


def test_unidad_canonica_deja_pasar_lo_que_no_conoce():
    """Un empaque raro se muestra tal cual antes que traducirse mal."""
    assert unidad_canonica("Huacal de 45 lb") == "Huacal de 45 lb"
    assert unidad_canonica("Paquete 6 und") == "Paquete 6 und"


def test_millar_no_se_traduce_a_unidad():
    """Millar es una unidad legítima —el plátano se cotiza así al por
    mayor— y aquí no se toca. El bug del plátano verde no estaba en la
    normalización sino en el fallback de exportar.py, que le colgaba la
    unidad MAYORISTA del catálogo a una oferta de góndola: "RD$18 / Millar",
    o sea 18 pesos por mil plátanos."""
    assert unidad_canonica("Millar") == "Millar"


# ------------------------------------------------------------------
# resumen_valor
# ------------------------------------------------------------------

def test_valor_es_la_mediana_no_el_minimo():
    """El titular de la tarjeta. Encabezar el mínimo contesta "¿dónde está
    más barato?", que es la pregunta de un directorio de tiendas, y además
    premia al más barato — lo que ESCALA.md prohíbe para el día que quien
    publique sea un productor."""
    r = resumen_valor([10.0, 20.0, 90.0], fuentes=3)
    assert r["valor_lb"] == 20.0


def test_la_mediana_aguanta_el_saco_mal_etiquetado():
    """Una cebolla real: la libra suelta contra un saco mal declarado. El
    promedio se va a 107; la mediana se queda donde está el mercado."""
    r = resumen_valor([46.0, 46.75, 229.0], fuentes=3)
    assert r["valor_lb"] == 46.75
    assert sum([46.0, 46.75, 229.0]) / 3 > 100      # el promedio sí se va


def test_dos_fuentes_dan_el_punto_medio():
    """El arroz selecto real: 33.50 de Nacional y 49.33 de Sirena."""
    r = resumen_valor([33.5, 49.33], fuentes=2)
    assert r["valor_lb"] == pytest.approx((33.5 + 49.33) / 2, abs=0.01)


def test_una_sola_fuente_devuelve_ese_precio():
    """La tarjeta lo rotula distinto —"un solo precio observado"— porque no
    hay mediana que valga, pero la cifra existe."""
    r = resumen_valor([75.0], fuentes=1)
    assert r["valor_lb"] == 75.0
    assert r["p25_lb"] == r["p75_lb"] == 75.0


def test_sin_datos_no_inventa_un_valor():
    r = resumen_valor([], fuentes=0)
    assert r["valor_lb"] is None
    assert r["p25_lb"] is None
    assert r["n_fuentes"] == 0


def test_ignora_los_ceros_y_los_nulos():
    """Un precio_lb en None es "el título no declaraba peso". Meterlo como
    cero hundiría la mediana."""
    r = resumen_valor([None, 0, 40.0, 60.0], fuentes=2)
    assert r["valor_lb"] == 50.0


def test_la_banda_sale_ordenada():
    r = resumen_valor([10.0, 20.0, 30.0, 40.0, 50.0], fuentes=5)
    assert r["p25_lb"] <= r["valor_lb"] <= r["p75_lb"]
    assert r["p25_lb"] == 20.0
    assert r["valor_lb"] == 30.0
    assert r["p75_lb"] == 40.0


def test_la_banda_es_la_misma_cuenta_que_usa_escala():
    """p25/p75 con interpolación lineal, igual que numpy. Si el mercado usa
    un método y la comparación de un productor usa otro, los dos números se
    contradicen en la misma página."""
    r = resumen_valor([1.0, 2.0, 3.0, 4.0], fuentes=4)
    assert r["p25_lb"] == 1.75
    assert r["valor_lb"] == 2.5
    assert r["p75_lb"] == 3.25


def test_el_orden_de_entrada_no_cambia_nada():
    a = resumen_valor([90.0, 10.0, 20.0], fuentes=3)
    b = resumen_valor([10.0, 20.0, 90.0], fuentes=3)
    assert a == b


def test_fuentes_se_pasa_tal_cual():
    """Son CADENAS distintas, no ofertas: Nacional con trece SKU de arroz es
    una sola fuente. Contar ofertas haría que un catálogo grande pareciera
    consenso de mercado."""
    r = resumen_valor([10.0, 11.0, 12.0, 13.0], fuentes=2)
    assert r["n_fuentes"] == 2
