"""Pruebas del scraper con HTML de ejemplo (no usan internet). Ejecutar usando: pytest"""



import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper import extraer_tabla_pib, limpiar_numero, validar

HTML_EJEMPLO = """
<html><body>
<table class="wikitable">
  <tr><th>Metropolitan area</th><th>Position</th><th>GDP (MXN)</th><th>GDP (USD)</th></tr>
  <tr><td>Valle de México</td><td>1</td><td>9,999</td><td>999</td></tr>
</table>
<table class="wikitable">
  <tr>
    <th>Position</th><th>State</th><th>Nominal GDP (MXN)</th><th>Nominal GDP (USD)</th>
    <th>GDP PPP (USD)</th><th>Growth</th><th>Nominal GDP per capita</th><th>% of national</th>
  </tr>
  <tr><td>1</td><td><span class="flagicon"><img alt=""/></span> <a>Mexico City</a><sup>[1]</sup></td>
      <td>5,041,647</td><td>248,690</td><td>508,000</td><td>+1.88%</td><td>$27,023</td><td>14%</td></tr>
  <tr><td>2</td><td><a>State of Mexico</a></td>
      <td>2,300,000</td><td>120,000</td><td>250,000</td><td>\u22120.50%</td><td>$6,500</td><td>8.1%</td></tr>
  <tr><td>3</td><td><a>Nuevo León</a></td>
      <td>2,200,000</td><td>115,000</td><td>240,000</td><td>+2.10%</td><td>$19,000</td><td>7.9%</td></tr>
  <tr><td>-</td><td>Mexico</td><td>33,913,877</td><td>1,852,225</td><td>3,417,188</td><td>+1.45%</td><td>$13,967</td><td>100%</td></tr>
  <tr><td colspan="2">Mexico</td><td>33,913,877</td><td>1,852,225</td></tr>
</table>
</body></html>
"""


def test_limpiar_numero_con_formatos_comunes():
    assert limpiar_numero("$27,023") == 27023
    assert limpiar_numero("+1.88%") == 1.88
    assert limpiar_numero("5,041,647[1]") == 5041647
    assert limpiar_numero("\u22120.50%") == -0.5


def test_limpiar_numero_devuelve_none_si_no_hay_numero():
    assert limpiar_numero("") is None
    assert limpiar_numero("-") is None
    assert limpiar_numero(None) is None


def test_extrae_la_tabla_correcta_y_omite_totales():
    df = extraer_tabla_pib(HTML_EJEMPLO)
    assert list(df["estado"]) == ["Mexico City", "State of Mexico", "Nuevo León"]
    assert list(df["posicion"]) == [1, 2, 3]


def test_los_valores_numericos_se_limpian():
    df = extraer_tabla_pib(HTML_EJEMPLO)
    primera = df.iloc[0]
    assert primera["pib_mxn_millones"] == 5041647
    assert primera["pib_per_capita_usd"] == 27023
    assert primera["crecimiento_pct"] == 1.88
    assert primera["porcentaje_nacional"] == 14
    assert df.iloc[1]["crecimiento_pct"] == -0.5


def test_error_si_no_hay_tabla():
    with pytest.raises(ValueError):
        extraer_tabla_pib("<html><body><p>nada</p></body></html>")


def test_validar_rechaza_tablas_incompletas():
    df = extraer_tabla_pib(HTML_EJEMPLO)  # solo 3 estados
    with pytest.raises(ValueError):
        validar(df)
