# Dashboard de mantenciones de tulipas / encajonadora-desencajonadora

import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Dashboard Mantenciones",
    layout="wide"
)

# =========================
# CONFIG
# =========================
SHEET_ID = "1Pr5c_3hnSxp37D5A-5bOCO5Pon9zIwRpA7xx709YEEA"
GID = "0"  # cambia si la hoja correcta tiene otro gid
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}"


# =========================
# FUNCIONES
# =========================
@st.cache_data
def cargar_datos():
    df = pd.read_csv(URL)

    # Limpiar nombres de columnas
    df.columns = [str(c).strip() for c in df.columns]

    # Eliminar columnas vacías tipo "Unnamed"
    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed", na=False)]

    # Eliminar filas completamente vacías
    df = df.dropna(how="all")

    # Estandarizar texto
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()

    # Convertir vacíos falsos a NaN
    df = df.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "None": pd.NA,
            "NaN": pd.NA
        }
    )

    # Parseo robusto de fecha en español:
    # "miércoles, 1 de abril de 2026" -> "1 abril 2026"
    if "FECHA" in df.columns:
        fecha_limpia = (
            df["FECHA"]
            .astype(str)
            .str.lower()
            .str.replace(r"^[^,]+,\s*", "", regex=True)   # quita "miércoles, "
            .str.replace(r"\s+de\s+", " ", regex=True)    # "1 de abril de 2026" -> "1 abril 2026"
            .str.strip()
        )

        meses = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
            "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
        }

        # Reemplazar nombre de mes por número
        for mes, num in meses.items():
            fecha_limpia = fecha_limpia.str.replace(fr"\b{mes}\b", num, regex=True)

        # Queda como "1 04 2026"
        df["FECHA_DT"] = pd.to_datetime(fecha_limpia, format="%d %m %Y", errors="coerce")

    # Numéricos
    for col in ["N° CABEZAL", "N° TULIPA"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def aplicar_filtros(df):
    st.sidebar.header("Filtros")

    turnos = st.sidebar.multiselect(
        "Turno",
        sorted(df["TURNO"].dropna().unique()) if "TURNO" in df.columns else [],
        default=sorted(df["TURNO"].dropna().unique()) if "TURNO" in df.columns else []
    )

    operadores = st.sidebar.multiselect(
        "Operador",
        sorted(df["OPERADOR"].dropna().unique()) if "OPERADOR" in df.columns else [],
        default=sorted(df["OPERADOR"].dropna().unique()) if "OPERADOR" in df.columns else []
    )

    equipos = st.sidebar.multiselect(
        "Equipo",
        sorted(df["EQUIPO"].dropna().unique()) if "EQUIPO" in df.columns else [],
        default=sorted(df["EQUIPO"].dropna().unique()) if "EQUIPO" in df.columns else []
    )

    formatos = st.sidebar.multiselect(
        "Formato",
        sorted(df["FORMATO"].dropna().unique()) if "FORMATO" in df.columns else [],
        default=sorted(df["FORMATO"].dropna().unique()) if "FORMATO" in df.columns else []
    )

    sabores = st.sidebar.multiselect(
        "Sabor",
        sorted(df["SABOR"].dropna().unique()) if "SABOR" in df.columns else [],
        default=sorted(df["SABOR"].dropna().unique()) if "SABOR" in df.columns else []
    )

    mantenciones = st.sidebar.multiselect(
        "Mantención",
        sorted(df["MANTENCIÓN"].dropna().unique()) if "MANTENCIÓN" in df.columns else [],
        default=sorted(df["MANTENCIÓN"].dropna().unique()) if "MANTENCIÓN" in df.columns else []
    )

    df_filtrado = df.copy()

    if "TURNO" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["TURNO"].isin(turnos)]
    if "OPERADOR" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["OPERADOR"].isin(operadores)]
    if "EQUIPO" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["EQUIPO"].isin(equipos)]
    if "FORMATO" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["FORMATO"].isin(formatos)]
    if "SABOR" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["SABOR"].isin(sabores)]
    if "MANTENCIÓN" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["MANTENCIÓN"].isin(mantenciones)]

    return df_filtrado


# =========================
# CARGA
# =========================
df = cargar_datos()
df_filtrado = aplicar_filtros(df)

# =========================
# HEADER
# =========================
st.title("Dashboard de Mantenciones")
st.caption("Registro de mantenciones de tulipas, encajonadora y desencajonadora")

# =========================
# KPIs
# =========================
total_mant = len(df_filtrado)
n_operadores = df_filtrado["OPERADOR"].nunique() if "OPERADOR" in df_filtrado.columns else 0
n_equipos = df_filtrado["EQUIPO"].nunique() if "EQUIPO" in df_filtrado.columns else 0
mant_top = (
    df_filtrado["MANTENCIÓN"].mode().iloc[0]
    if "MANTENCIÓN" in df_filtrado.columns and not df_filtrado["MANTENCIÓN"].dropna().empty
    else "-"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total mantenciones", total_mant)
c2.metric("Operadores", n_operadores)
c3.metric("Equipos", n_equipos)
c4.metric("Mantención más frecuente", mant_top)

# =========================
# GRÁFICOS
# =========================
col1, col2 = st.columns(2)

with col1:
    if "FECHA_DT" in df_filtrado.columns and not df_filtrado["FECHA_DT"].dropna().empty:
        serie = (
            df_filtrado.groupby("FECHA_DT")
            .size()
            .reset_index(name="Cantidad")
            .sort_values("FECHA_DT")
        )
        fig = px.line(
            serie,
            x="FECHA_DT",
            y="Cantidad",
            markers=True,
            title="Mantenciones por día"
        )
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if "MANTENCIÓN" in df_filtrado.columns:
        mant = (
            df_filtrado["MANTENCIÓN"]
            .value_counts()
            .reset_index()
        )
        mant.columns = ["MANTENCIÓN", "Cantidad"]
        fig = px.bar(
            mant,
            x="MANTENCIÓN",
            y="Cantidad",
            title="Frecuencia por tipo de mantención"
        )
        st.plotly_chart(fig, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    if "OPERADOR" in df_filtrado.columns:
        op = df_filtrado["OPERADOR"].value_counts().reset_index()
        op.columns = ["OPERADOR", "Cantidad"]
        fig = px.bar(
            op,
            x="OPERADOR",
            y="Cantidad",
            title="Mantenciones por operador"
        )
        st.plotly_chart(fig, use_container_width=True)

with col4:
    if "EQUIPO" in df_filtrado.columns:
        eq = df_filtrado["EQUIPO"].value_counts().reset_index()
        eq.columns = ["EQUIPO", "Cantidad"]
        fig = px.pie(
            eq,
            names="EQUIPO",
            values="Cantidad",
            title="Distribución por equipo"
        )
        st.plotly_chart(fig, use_container_width=True)

col5, col6 = st.columns(2)

with col5:
    if "TURNO" in df_filtrado.columns:
        turno = df_filtrado["TURNO"].value_counts().reset_index()
        turno.columns = ["TURNO", "Cantidad"]
        fig = px.bar(
            turno,
            x="TURNO",
            y="Cantidad",
            title="Mantenciones por turno"
        )
        st.plotly_chart(fig, use_container_width=True)

with col6:
    if "FORMATO" in df_filtrado.columns:
        formato = df_filtrado["FORMATO"].value_counts().reset_index()
        formato.columns = ["FORMATO", "Cantidad"]
        fig = px.bar(
            formato,
            x="FORMATO",
            y="Cantidad",
            title="Mantenciones por formato"
        )
        st.plotly_chart(fig, use_container_width=True)

# =========================
# ANÁLISIS ADICIONAL
# =========================
st.subheader("Cruce equipo vs mantención")
if {"EQUIPO", "MANTENCIÓN"}.issubset(df_filtrado.columns):
    tabla_cruce = pd.crosstab(df_filtrado["EQUIPO"], df_filtrado["MANTENCIÓN"])
    st.dataframe(tabla_cruce, use_container_width=True)

st.subheader("Detalle de registros")
columnas_mostrar = [
    c for c in [
        "FECHA", "TURNO", "OPERADOR", "EQUIPO", "FORMATO", "SABOR",
        "N° CABEZAL", "N° TULIPA", "MANTENCIÓN", "OBSERVACIÓN"
    ] if c in df_filtrado.columns
]
st.dataframe(df_filtrado[columnas_mostrar], use_container_width=True)

# =========================
# DESCARGA
# =========================
csv = df_filtrado.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Descargar datos filtrados en CSV",
    data=csv,
    file_name="mantenciones_filtradas.csv",
    mime="text/csv"
)