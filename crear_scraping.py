"""Crea todos los archivos del proyecto de web scraping en esta carpeta.

Uso: python crear_scraping.py
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent

ARCHIVOS = {
    'scraper.py': r'''"""Web scraping del PIB de los estados de México desde Wikipedia.

Reglas de uso responsable que sigue este módulo:
- Una sola petición HTTP por ejecución (no se hace scraping masivo).
- Se identifica con un User-Agent descriptivo, como pide Wikimedia.
- Usa un tiempo máximo de espera (timeout).
- Los datos se guardan en un CSV local para no volver a pedir la página.
- El contenido de Wikipedia se publica bajo licencia CC BY-SA 4.0 (hay que citar la fuente).
"""

import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://en.wikipedia.org/wiki/List_of_Mexican_states_by_GDP"
# Cambia el correo por el tuyo o el del equipo.
USER_AGENT = "ProyectoEscolarENES/1.0 (proyecto academico; contacto: TU_CORREO@ejemplo.com)"
CSV_PATH = Path(__file__).resolve().parent / "data" / "pib_estados.csv"

COLUMNAS = [
    "posicion",
    "estado",
    "pib_mxn_millones",
    "pib_usd_millones",
    "pib_ppp_usd_millones",
    "crecimiento_pct",
    "pib_per_capita_usd",
    "porcentaje_nacional",
]


def descargar_html(url=URL, timeout=20):
    """Descarga la página. Lanza una excepción si la petición falla."""
    respuesta = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    respuesta.raise_for_status()
    return respuesta.text


def limpiar_numero(texto):
    """Convierte textos como '$27,023', '+1.88%' o '5,041,647[1]' en número.

    Devuelve None si no hay un número reconocible.
    """
    if texto is None:
        return None
    texto = re.sub(r"\[.*?\]", "", str(texto))          # quita notas como [1]
    texto = texto.replace("\u2212", "-").replace("\xa0", " ")  # menos unicode y espacio duro
    texto = re.sub(r"[^0-9.\-]", "", texto)              # deja solo dígitos, punto y signo
    if texto in ("", "-", "."):
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def _texto_celda(celda):
    """Texto limpio de una celda (sin notas al pie ni espacios raros)."""
    for sup in celda.find_all("sup"):
        sup.decompose()
    return re.sub(r"\s+", " ", celda.get_text(" ", strip=True)).strip()


def _nombre_columna(encabezado):
    """Asocia un encabezado de la tabla con el nombre de columna que usamos."""
    h = encabezado.lower()
    if "per capita" in h:
        return "pib_per_capita_usd"
    if "ppp" in h:
        return "pib_ppp_usd_millones"
    if "mxn" in h:
        return "pib_mxn_millones"
    if "usd" in h:
        return "pib_usd_millones"
    if "growth" in h:
        return "crecimiento_pct"
    if "%" in h or "national" in h:
        return "porcentaje_nacional"
    if "position" in h or "rank" in h:
        return "posicion"
    if "state" in h or "entity" in h:
        return "estado"
    return None


def _encabezados(tabla):
    """Devuelve la lista de encabezados de la primera fila con <th>, o None."""
    for fila in tabla.find_all("tr"):
        ths = fila.find_all("th")
        if len(ths) >= 4:
            return [_texto_celda(th) for th in ths]
    return None


def extraer_tabla_pib(html):
    """Busca en el HTML la tabla de PIB por estado y la devuelve como DataFrame."""
    soup = BeautifulSoup(html, "html.parser")
    for tabla in soup.find_all("table"):
        encabezados = _encabezados(tabla)
        if not encabezados:
            continue
        nombres = [_nombre_columna(h) for h in encabezados]
        if "estado" not in nombres or "pib_mxn_millones" not in nombres:
            continue  # no es la tabla de estados (por ejemplo, la de áreas metropolitanas)

        filas = []
        for fila in tabla.find_all("tr"):
            celdas = fila.find_all(["th", "td"])
            if len(celdas) != len(nombres):
                continue  # encabezado, fila de totales u otra fila irregular
            textos = [_texto_celda(c) for c in celdas]
            registro = dict(zip(nombres, textos))
            posicion = limpiar_numero(registro.get("posicion"))
            if posicion is None:
                continue  # se omiten filas sin posición, como el total nacional
            fila_limpia = {"posicion": int(posicion), "estado": registro["estado"]}
            for columna in COLUMNAS[2:]:
                fila_limpia[columna] = limpiar_numero(registro.get(columna))
            filas.append(fila_limpia)

        if filas:
            return pd.DataFrame(filas, columns=COLUMNAS)
    raise ValueError("No se encontró la tabla de PIB por estado; la página pudo cambiar.")


def validar(df):
    """Verificaciones básicas de calidad. Lanza ValueError si algo no cuadra."""
    if len(df) < 30:
        raise ValueError(f"Se esperaban unos 32 estados y se obtuvieron {len(df)}.")
    if df["estado"].eq("").any():
        raise ValueError("Hay estados sin nombre.")
    if df["pib_mxn_millones"].isna().any():
        raise ValueError("Hay estados sin PIB en pesos.")
    return df


def scrapear(url=URL):
    """Descarga, extrae y valida la tabla. Devuelve un DataFrame."""
    return validar(extraer_tabla_pib(descargar_html(url)))


def guardar_csv(df, ruta=CSV_PATH):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)


def cargar_csv(ruta=CSV_PATH):
    """Carga los datos guardados, o None si todavía no existen."""
    if ruta.exists():
        return pd.read_csv(ruta)
    return None
''',
    'app.py': r'''"""Interfaz en Streamlit para explorar el PIB de los estados de México.

Ejecutar con: streamlit run app.py
"""

import streamlit as st

from scraper import URL, cargar_csv, guardar_csv, scrapear

METRICAS = {
    "PIB nominal (millones de MXN)": "pib_mxn_millones",
    "PIB nominal (millones de USD)": "pib_usd_millones",
    "PIB PPP (millones de USD)": "pib_ppp_usd_millones",
    "PIB per cápita (USD)": "pib_per_capita_usd",
    "Crecimiento (%)": "crecimiento_pct",
    "Participación en el PIB nacional (%)": "porcentaje_nacional",
}

st.set_page_config(page_title="PIB de los estados de México", layout="wide")
st.title("PIB de los estados de México")
st.caption(
    "Datos obtenidos con web scraping de Wikipedia (licencia CC BY-SA 4.0). "
    f"Fuente: {URL}"
)

# ---------- Obtención de datos ----------
with st.sidebar:
    st.header("Datos")
    if st.button("Actualizar datos (hacer scraping)", type="primary"):
        try:
            with st.spinner("Descargando y procesando la página..."):
                nuevos = scrapear()
            guardar_csv(nuevos)
            st.success(f"Datos actualizados: {len(nuevos)} estados.")
        except Exception as error:  # red caída, página cambiada, etc.
            st.error(f"No se pudo hacer el scraping: {error}")

df = cargar_csv()
if df is None:
    st.info("Aún no hay datos. Pulsa **Actualizar datos (hacer scraping)** en la barra lateral.")
    st.stop()

with st.sidebar:
    st.header("Visualización")
    etiqueta = st.selectbox("Indicador", list(METRICAS.keys()))
    cantidad = st.slider("Cuántos estados mostrar", 5, len(df), 10)
    orden = st.radio("Orden", ["Mayor a menor", "Menor a mayor"])

columna = METRICAS[etiqueta]
datos = df.dropna(subset=[columna]).sort_values(columna, ascending=(orden == "Menor a mayor"))
datos = datos.head(cantidad)

# ---------- Resultados ----------
c1, c2, c3 = st.columns(3)
c1.metric("Estados en la tabla", len(df))
c2.metric(f"Máximo: {datos.iloc[0]['estado']}", f"{datos.iloc[0][columna]:,.2f}")
c3.metric("Promedio del indicador", f"{df[columna].mean():,.2f}")

st.subheader(etiqueta)
st.bar_chart(datos.set_index("estado")[columna])

st.subheader("Relación entre PIB per cápita y crecimiento")
st.scatter_chart(df, x="pib_per_capita_usd", y="crecimiento_pct")

st.subheader("Tabla completa")
st.dataframe(df, use_container_width=True, hide_index=True)
st.download_button(
    "Descargar CSV",
    df.to_csv(index=False).encode("utf-8"),
    file_name="pib_estados.csv",
    mime="text/csv",
)
''',
    'requirements.txt': r'''streamlit>=1.30
requests>=2.31
beautifulsoup4>=4.12
pandas>=2.0
pytest>=7.0
''',
    'README.md': r'''# Web scraping de información económica

<!-- Rúbrica: el README es el extenso técnico y debe redactarlo el equipo con sus propias palabras.
     No usar IA para escribirlo, reescribirlo ni resumirlo. Estos son solo los apartados obligatorios. -->

## Integrantes y responsabilidades

## Resumen

## Introducción

### Problema

### Objetivos

## Solución y evidencia

## Conclusiones

## Reproducibilidad
''',
    '.gitignore': r'''__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
''',
    'tests/test_scraper.py': r'''"""Pruebas del scraper con HTML de ejemplo (no usan internet). Ejecutar con: pytest"""

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
''',
}

for nombre, contenido in ARCHIVOS.items():
    ruta = BASE / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    print("Creado:", ruta)

print()
print("Listo. Ahora ejecuta:")
print("  python -m pip install -r requirements.txt")
print("  python -m pytest")
print("  streamlit run app.py")
