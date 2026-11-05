"""Interfaz en Streamlit para explorar el PIB de los estados de México.

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
