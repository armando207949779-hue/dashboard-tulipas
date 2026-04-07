# Dashboard de mantenciones de tulipas / encajonadora-desencajonadora

import pandas as pd
import streamlit as st
import plotly.express as px
import requests
from io import StringIO

st.set_page_config(page_title="Dashboard Mantenciones", layout="wide")

# =========================
# CONFIG
# =========================
SHEET_ID = "1Pr5c_3hnSxp37D5A-5bOCO5Pon9zIwRpA7xx709YEEA"
GID = "0"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================
# BOTÓN DE ACTUALIZACIÓN
# =========================
col_btn1, col_btn2 = st.columns([1, 5])
with col_btn1:
    if st.button("Actualizar datos"):
        st.cache_data.clear()
        st.rerun()

with col_btn2:
    st.caption("Si cambias datos en Google Sheets, presiona este botón para recargar.")

# =========================
# FUNCIONES
# =========================
@st.cache_data(ttl=10)
def cargar_datos():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(URL, headers=headers, timeout=20)
        response.raise_for_status()

        if not response.text.strip():
            raise ValueError("La respuesta del Google Sheet está vacía.")

        df = pd.read_csv(StringIO(response.text))

    except Exception as e:
        st.error("No se pudo leer Google Sheets.")
        st.error("Revisa que la hoja esté publicada o compartida como pública, y que el GID sea correcto.")
        st.code(str(e))
        st.stop()

    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed", na=False)]
    df = df.dropna(how="all")

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()

    df = df.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaN": pd.NA})

    for col in ["TURNO", "OPERADOR", "EQUIPO", "FORMATO", "SABOR", "MANTENCIÓN", "OBSERVACIÓN"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()

    if "MANTENCIÓN" in df.columns:
        df["MANTENCIÓN"] = df["MANTENCIÓN"].str.replace(
            r"OTRO \(ESPECIFICAR\).*", "OTRO (ESPECIFICAR)", regex=True
        )

    cols_clave = [
        "FECHA", "TURNO", "OPERADOR", "EQUIPO", "FORMATO", "SABOR",
        "N° CABEZAL", "N° TULIPA", "MANTENCIÓN", "OBSERVACIÓN"
    ]
    cols_clave = [c for c in cols_clave if c in df.columns]
    if cols_clave:
        df = df.drop_duplicates(subset=cols_clave)

    if "FECHA" in df.columns:
        fecha_limpia = (
            df["FECHA"]
            .astype(str)
            .str.lower()
            .str.replace(r"^[^,]+,\s*", "", regex=True)
            .str.replace(r"\s+de\s+", " ", regex=True)
            .str.strip()
        )

        meses = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
            "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
        }

        for mes, num in meses.items():
            fecha_limpia = fecha_limpia.str.replace(fr"\b{mes}\b", num, regex=True)

        df["FECHA_DT"] = pd.to_datetime(fecha_limpia, format="%d %m %Y", errors="coerce")

    for col in ["N° CABEZAL", "N° TULIPA"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def aplicar_filtros(df):
    st.sidebar.header("Filtros")

    def multiselect_col(nombre):
        if nombre in df.columns:
            vals = sorted(df[nombre].dropna().unique())
            return st.sidebar.multiselect(nombre, vals, default=vals)
        return []

    turnos = multiselect_col("TURNO")
    operadores = multiselect_col("OPERADOR")
    equipos = multiselect_col("EQUIPO")
    formatos = multiselect_col("FORMATO")
    sabores = multiselect_col("SABOR")
    mantenciones = multiselect_col("MANTENCIÓN")

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


def obtener_criticidad(df_filtrado):
    cols_req = ["N° CABEZAL", "N° TULIPA", "EQUIPO", "FORMATO"]
    if not all(c in df_filtrado.columns for c in cols_req):
        return None, None, None, None, None, None

    base = df_filtrado.dropna(subset=["N° CABEZAL", "N° TULIPA"]).copy()
    if base.empty:
        return None, None, None, None, None, None

    pesos_mant = {
        "CAMBIO CUERPO TULIPA PLÁSTICA": 4,
        "CAMBIO DE GOMA TULIPA": 3,
        "CAMBIO DE VÁSTAGO": 2,
        "CAMBIO DE RESORTE": 2,
        "CAMBIO DE SEGURO DE VÁSTAGO": 2,
        "CAMBIO DE CONECTOR NEUMÁTICO": 2,
        "OTRO (ESPECIFICAR)": 1
    }

    if "MANTENCIÓN" in base.columns:
        base["PESO"] = base["MANTENCIÓN"].map(pesos_mant).fillna(1)
    else:
        base["PESO"] = 1

    ranking_cabezal = (
        base.groupby("N° CABEZAL", as_index=False)
        .agg(Frecuencia=("N° CABEZAL", "size"), Criticidad=("PESO", "sum"))
        .sort_values(["Criticidad", "Frecuencia", "N° CABEZAL"], ascending=[False, False, True])
    )

    ranking_tulipa = (
        base.groupby("N° TULIPA", as_index=False)
        .agg(Frecuencia=("N° TULIPA", "size"), Criticidad=("PESO", "sum"))
        .sort_values(["Criticidad", "Frecuencia", "N° TULIPA"], ascending=[False, False, True])
    )

    ranking_combo = (
        base.groupby(["N° CABEZAL", "N° TULIPA", "EQUIPO", "FORMATO"], as_index=False)
        .agg(Frecuencia=("PESO", "size"), Criticidad=("PESO", "sum"))
        .sort_values(
            ["Criticidad", "Frecuencia", "N° CABEZAL", "N° TULIPA"],
            ascending=[False, False, True, True]
        )
    )

    cabezal_critico = ranking_cabezal.iloc[0] if not ranking_cabezal.empty else None
    tulipa_critica = ranking_tulipa.iloc[0] if not ranking_tulipa.empty else None
    combo_critico = ranking_combo.iloc[0] if not ranking_combo.empty else None

    return cabezal_critico, tulipa_critica, combo_critico, ranking_combo, ranking_cabezal, ranking_tulipa


df = cargar_datos()
df_filtrado = aplicar_filtros(df)

st.title("Dashboard de Mantenciones")
st.caption("Registro de mantenciones de tulipas, encajonadora y desencajonadora")

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

cabezal_critico, tulipa_critica, combo_critico, ranking_combo, ranking_cabezal, ranking_tulipa = obtener_criticidad(df_filtrado)

st.subheader("Respuesta automática: criticidad")

if combo_critico is not None:
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Cabezal más crítico", int(cabezal_critico["N° CABEZAL"]))
    a2.metric("Tulipa más crítica", int(tulipa_critica["N° TULIPA"]))
    a3.metric("Equipo crítico", str(combo_critico["EQUIPO"]))
    a4.metric("Formato crítico", str(combo_critico["FORMATO"]))

    st.info(
        f"Cabezal más crítico: {int(cabezal_critico['N° CABEZAL'])} | "
        f"Tulipa más crítica: {int(tulipa_critica['N° TULIPA'])} | "
        f"Combinación más crítica: Cabezal {int(combo_critico['N° CABEZAL'])} + "
        f"Tulipa {int(combo_critico['N° TULIPA'])} en {combo_critico['EQUIPO']} "
        f"formato {combo_critico['FORMATO']}."
    )

    b1, b2 = st.columns(2)
    with b1:
        st.markdown("**Ranking de cabezales**")
        st.dataframe(ranking_cabezal, use_container_width=True)

    with b2:
        st.markdown("**Ranking de tulipas**")
        st.dataframe(ranking_tulipa, use_container_width=True)

    st.markdown("**Top combinaciones cabezal + tulipa + equipo + formato**")
    st.dataframe(ranking_combo.head(10), use_container_width=True)

else:
    st.warning("No hay datos suficientes para calcular criticidad.")

col1, col2 = st.columns(2)

with col1:
    if "FECHA_DT" in df_filtrado.columns and not df_filtrado["FECHA_DT"].dropna().empty:
        serie = (
            df_filtrado.groupby("FECHA_DT")
            .size()
            .reset_index(name="Cantidad")
            .sort_values("FECHA_DT")
        )
        fig = px.line(serie, x="FECHA_DT", y="Cantidad", markers=True, title="Mantenciones por día")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if "MANTENCIÓN" in df_filtrado.columns:
        mant = df_filtrado["MANTENCIÓN"].value_counts().reset_index()
        mant.columns = ["MANTENCIÓN", "Cantidad"]
        fig = px.bar(mant, x="MANTENCIÓN", y="Cantidad", title="Frecuencia por tipo de mantención")
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Detalle de registros")
columnas_mostrar = [
    c for c in [
        "FECHA", "TURNO", "OPERADOR", "EQUIPO", "FORMATO", "SABOR",
        "N° CABEZAL", "N° TULIPA", "MANTENCIÓN", "OBSERVACIÓN"
    ] if c in df_filtrado.columns
]
st.dataframe(df_filtrado[columnas_mostrar], use_container_width=True)

csv = df_filtrado.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Descargar datos filtrados en CSV",
    data=csv,
    file_name="mantenciones_filtradas.csv",
    mime="text/csv"
)