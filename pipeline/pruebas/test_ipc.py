"""Pruebas del IPC del Banco Central. Sin red: se arma un xlsx mínimo con
la misma forma del real y se comprueba el contrato.

Lo que se cuida aquí es lo que se rompe callado: que el año se arrastre
bien por las columnas (el Excel solo lo escribe una vez, en enero), que la
fila de rótulos se encuentre aunque cambien las filas vacías de arriba, y
que la estacionalidad no le crea a un año suelto.

    python -m pytest pipeline/pruebas -q
"""

import zipfile

import pytest

from pipeline.ipc import _columna, _estacionalidad, _mediana, _meses, construir

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NSR = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _celda(ref, valor):
    if isinstance(valor, str):
        return f'<c r="{ref}" t="inlineStr"><is><t>{valor}</t></is></c>'
    return f'<c r="{ref}"><v>{valor}</v></c>'


def _xlsx(ruta, filas):
    """filas: lista de (numero_de_fila, {letra: valor})."""
    cuerpo = ""
    for n, celdas in filas:
        cs = "".join(_celda(f"{L}{n}", v) for L, v in celdas.items())
        cuerpo += f'<row r="{n}">{cs}</row>'
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("xl/workbook.xml",
                   f'<workbook xmlns="{NS}" xmlns:r="{NSR}"><sheets>'
                   f'<sheet name="2020-2026" sheetId="1" r:id="rId1"/>'
                   f"</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/relationships"><Relationship Id="rId1" '
                   'Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<worksheet xmlns="{NS}"><sheetData>{cuerpo}</sheetData></worksheet>')


# La yuca sube todo el tramo: 13 meses seguidos para que haya interanual.
MESES_13 = ["Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio"]
LETRAS = ["G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"]


@pytest.fixture
def libro(tmp_path):
    ruta = tmp_path / "ipc.xlsx"
    # El año se escribe UNA vez: en la primera columna de ese año.
    anios = {"G": "2025", "M": "2026"}
    rotulos = dict(zip(LETRAS, MESES_13))
    rotulos.update({"A": "Grupo", "B": "Subgrupo", "C": "Clase",
                    "D": "Subclase", "E": "Artículo", "F": "Ponderación"})
    alimentos = {"A": "01 Alimentos y Bebidas No Alcohólicas", "F": 23.8}
    yuca = {"E": "0117201 Yuca", "F": 0.345}
    for i, L in enumerate(LETRAS):
        alimentos[L] = 100 + i
        yuca[L] = 100 + i * 2
    _xlsx(ruta, [(1, anios), (3, rotulos), (4, alimentos), (9, yuca)])
    return ruta


def test_columna():
    assert _columna("A1") == 0
    assert _columna("G12") == 6
    assert _columna("AA3") == 26


def test_el_anio_se_arrastra(libro):
    from pipeline.ipc import _leer_hoja
    cols = _meses(_leer_hoja(libro, "2020-2026"))
    assert cols[0][1] == "2025-07"
    # Diciembre sigue siendo 2025 aunque el Excel no lo repita...
    assert cols[5][1] == "2025-12"
    # ...y enero ya es 2026, que ahí sí lo escribe.
    assert cols[6][1] == "2026-01"
    assert cols[-1][1] == "2026-07"


def test_construir(libro):
    d = construir(libro)
    assert d["alimentos"]["mes"] == "2026-07"
    assert len(d["rubros"]) == 1
    r = d["rubros"][0]
    assert r["id"] == "yuca"
    # Femenino: la página escribe "más cara", no "más caro".
    assert r["genero"] == "f"
    # Un rubro del IPC cubre VARIAS variedades de Kcuesta, nunca al revés.
    assert r["rubros_kcuesta"] == ["yuca-bilin"]
    assert r["indice"] == 124.0
    assert r["interanual"] == 24.0
    assert d["_meta"]["ultimo_mes"] == "2026-07"


def test_sin_columnas_de_mes_revienta(tmp_path):
    """Si el Banco Central cambia el formato, que falle fuerte y no
    publique una página vacía como si no pasara nada."""
    ruta = tmp_path / "raro.xlsx"
    _xlsx(ruta, [(3, {"A": "Grupo", "G": "Enero"})])
    with pytest.raises(RuntimeError):
        construir(ruta)


def test_mediana_aguanta_el_ano_raro():
    assert _mediana([0.01, 0.02, 0.03]) == 0.02
    # Un enero con 40 % no puede volverse "la costumbre" del mes.
    normal = [0.01, 0.01, 0.02, 0.02]
    assert _mediana(normal + [0.40]) < 0.03


def test_estacionalidad_por_numero_de_mes():
    serie = {"2025-01": 100.0, "2025-02": 90.0, "2025-03": 99.0,
             "2026-01": 110.0, "2026-02": 99.0, "2026-03": 108.9}
    est = _estacionalidad(serie)
    # Febrero baja 10 % los dos años; marzo sube 10 %.
    assert est["02"] == pytest.approx(-10.0, abs=0.1)
    assert est["03"] == pytest.approx(10.0, abs=0.1)
    # Enero no tiene mes anterior dentro de la serie más que 2025-12,
    # que no existe: no se inventa.
    assert "01" not in est
