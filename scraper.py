"""Web scraping del PIB de los estados de México desde Wikipedia.

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
USER_AGENT = "ProyectoEscolarENES/1.0 (proyecto academico; contacto: victoralfonsogonzalezserrano17@gmail.com)"
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
