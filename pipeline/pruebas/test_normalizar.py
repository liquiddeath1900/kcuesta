"""Pruebas de normalización. Sin red: contrato puro sobre datos reales.

Los casos NO son inventados — son categorías y nombres tomados tal cual de
Sirena, Nacional, Fruttissimo, MERCADOM y los cuadros del Ministerio. Es la
capa donde un error no revienta nada: solo mete un precio equivocado en la
serie, en silencio, hasta que alguien cotiza contra él.

    python -m pytest pipeline/pruebas -q
"""

import pytest

from pipeline.normalizar import (
    a_numero,
    categoria_capturable,
    clave,
    foto_elegible,
    libras_de_titulo,
    precio_por_unidad,
    unidades_por_empaque,
)


# ------------------------------------------------------------------
# Nombres: el mismo plátano en cinco fuentes distintas
# ------------------------------------------------------------------
@pytest.mark.parametrize("crudo, esperado", [
    ("PLATANO VERDE", "platano verde"),
    ("Platano Verde Und", "platano verde"),
    ("Plátano Verde, Und", "platano verde"),
    ("Plátano (Barahona), grande", "platano barahona"),
    ("Plátano (Maeño), grande", "platano maeno"),
    ("Ñame (Mina)", "name mina"),
    ("Habichuela roja (José Beta)", "habichuela roja jose beta"),
    ("Arroz (Súper Selecto), primera", "arroz super selecto"),
    ("Batata Criolla Amarilla Fresca – Libra (Aprox. 1–2 unidades)", "batata criolla amarilla"),
])
def test_clave_canoniza(crudo, esperado):
    assert clave(crudo) == esperado


def test_variedad_no_se_colapsa():
    """Barahona y Maeño son precios distintos; fundirlos arruina la serie."""
    assert clave("Plátano (Barahona), grande") != clave("Plátano (Maeño), grande")


def test_origen_es_variedad_no_relleno():
    """Importado y criollo marcan precios distintos, no son adjetivos sueltos.

    El ajo importado y el criollo no valen lo mismo y el Ministerio los
    lista por separado. Tratarlos como ruido fundía dos series en una.
    """
    assert clave("Ajo (Importado)") != clave("Ajo criollo")
    assert "importado" in clave("Ajo (Importado)")
    assert "criolla" in clave("Cebolla roja criolla")


# ------------------------------------------------------------------
# Números al estilo contable de los cuadros del Ministerio
# ------------------------------------------------------------------
@pytest.mark.parametrize("crudo, esperado", [
    ("1,234.50", 1234.50),
    (" 11,500.00 ", 11500.00),
    ("(25.00)", -25.00),          # negativo entre paréntesis
    ("-", None),
    ("–", None),
    ("", None),
    ("RD$ 180.00", 180.00),
])
def test_a_numero(crudo, esperado):
    assert a_numero(crudo) == esperado


# ------------------------------------------------------------------
# Unidades: comparar un millar contra una unidad suelta
# ------------------------------------------------------------------
@pytest.mark.parametrize("unidad, esperado", [
    ("Millar", 1000),
    ("Quintal", 100),
    ("Ciento", 100),
    ("Saco de 50 lb", 50),
    ("Huacal de 45 lb", 45),
    ("Saco de 600 und", 600),
    ("Saco/100 libra", 100),
    ("Fardo/12 Ud", 12),
    ("Libra", 1),
    ("lb", 1),
])
def test_unidades_por_empaque(unidad, esperado):
    assert unidades_por_empaque(unidad) == esperado


def test_unidad_desconocida_no_asume_uno():
    """Devolver None es lo correcto. Asumir 1 mete un error de 100x."""
    assert unidades_por_empaque("caja rara sin medida") is None
    assert precio_por_unidad(2700, "caja rara sin medida") is None


def test_precio_por_unidad_normaliza():
    assert precio_por_unidad(17000, "Millar") == 17.0     # plátano
    assert precio_por_unidad(2700, "Quintal") == 27.0     # yuca


# ------------------------------------------------------------------
# Categorías: tres taxonomías incompatibles, un solo criterio
# ------------------------------------------------------------------
@pytest.mark.parametrize("categoria, captura, foto", [
    # Fruttissimo
    ("Frutas Frescas",                       True,  True),
    ("Vegetales Frescos",                    True,  True),
    ("Frutas Importadas",                    True,  True),
    ("Víveres Frescos",                      True,  True),
    ("Vegetales Orgánicos",                  True,  True),
    ("Huevos y Lácteos",                     True,  False),
    ("Granos, Legumbres y Cereales",         True,  False),
    ("Frutas Congeladas",                    False, False),
    ("Pulpa de Frutas Congeladas",           False, False),
    ("Nueces, Frutos Secos y Deshidratados", False, False),
    ("Despensa",                             False, False),
    ("Cervezas",                             False, False),
    # Nacional
    ("Frutas Cítricas",                      True,  True),
    ("Frutas Tropicales y Exóticas",         True,  True),
    ("Carnes/Res",                           True,  True),
    ("Carnes/Sustitutos Cárnicos",           False, False),
    # Sirena
    ("Supermercado/Frutas y Vegetales/Vegetales Frescos", True, True),
    ("Supermercado/Despensa/Arroz, Habichuelas y otros granos/Arroz", True, False),
    ("Supermercado/Congelados/Frutas Congeladas", False, False),
    ("Supermercado/Despensa/Conservas, Enlatados y aceitunas/Conserva de frutas", False, False),
])
def test_clasificacion_de_categorias(categoria, captura, foto):
    assert categoria_capturable(categoria) is captura
    assert foto_elegible(categoria) is foto


def test_la_hoja_manda_sobre_el_ancestro():
    """Una góndola válida no le abre la puerta a un hijo procesado."""
    assert categoria_capturable("Carnes") is True
    assert categoria_capturable("Carnes/Sustitutos Cárnicos") is False


# ------------------------------------------------------------------
# Tamaño del empaque: sin esto la comparación entre cadenas miente
# ------------------------------------------------------------------
@pytest.mark.parametrize("titulo, libras", [
    ("Pera Forelle Fresca – Caja 22 lb",                    22.0),
    ("Papa Fresca – Saco (Aprox. 47–50 lb)",                 48.5),   # promedio del rango
    ("Ají Gustoso Fresco – Pack 8oz",                         0.5),
    ("Papas Gold Frescas – Caja Retail (6 Packs de 24 oz)",   9.0),   # 6 × 24 oz
    ("Arroz Campos Premium – 1 lb",                           1.0),
    ("Cebolla Amarilla – Saco 50 lb",                        50.0),
    ("Leche Entera 1 kg",                                 2.2046),
    # Vendido POR libra, sin número: es una libra.
    ("Aji Cubanela,Lb (Aprox. 4 unidades Por Libra)",         1.0),
    ("Filete De Pechuga Pollo Cibao Lb",                      1.0),
    ("Batata Criolla Amarilla Fresca – Libra (Aprox. 1–2 unidades)", 1.0),
    # No dice cuánto trae: None, nunca un supuesto.
    ("Limón Verde Tahití – Caja y Malla",                    None),
    ("Coco De Agua, Und",                                    None),
])
def test_libras_de_titulo(titulo, libras):
    assert libras_de_titulo(titulo) == libras


def test_saco_y_libra_se_vuelven_comparables():
    """El bug que el agrupamiento destapó.

    La cadena vende la cebolla suelta por libra a RD$46 y en saco de 50 lb a
    RD$10,750. Sin normalizar, el rubro decía 'RD$46 – RD$10,750' y el saco
    parecía 234 veces más caro. Por libra son RD$46 contra RD$215: más caro
    igual, pero 4.7 veces, no 234.
    """
    suelta_lb = libras_de_titulo("Cebolla Amarilla Lb")
    saco_lb = libras_de_titulo("Cebolla Amarilla – Saco 50 lb")
    assert suelta_lb == 1.0 and saco_lb == 50.0

    precio_suelta = 46.0 / suelta_lb
    precio_saco = 10750.0 / saco_lb
    assert round(precio_saco, 2) == 215.0
    assert precio_saco / precio_suelta < 5        # no 234x


def test_empaque_sin_peso_no_se_inventa():
    """Igual que con las unidades del mayorista: mejor un hueco que un supuesto."""
    assert libras_de_titulo("Limón Verde Tahití – Caja y Malla") is None
    assert libras_de_titulo("") is None
    assert libras_de_titulo(None) is None


def test_grano_se_captura_pero_no_se_espeja_su_foto():
    """El precio del arroz sirve; su foto es el saco con la marca encima."""
    ruta = "Supermercado/Despensa/Arroz, Habichuelas y otros granos/Arroz"
    assert categoria_capturable(ruta) is True
    assert foto_elegible(ruta) is False
