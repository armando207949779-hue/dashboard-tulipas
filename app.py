# Dashboard de mantenciones de tulipas / encajonadora-desencajonadora
# Elaborado por: Enrique Brun
# Jefe de Operaciones: Gaston Flores

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Mantenciones", layout="wide")

# =========================
# CONFIG
# =========================
SHEET_ID = "1Pr5c_3hnSxp37D5A-5bOCO5Pon9zIwRpA7xx709YEEA"
GID = "0"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}"

# =========================
# ESTILO
# =========================
st.markdown("""
<style>
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}
[data-testid="stMetric"] {
    background-color: #f7f9fc;
    border: 1px solid #e6ebf2;
    padding: 12px;
    border-radius: 12px;
}
.seccion {
    padding: 0.8rem 1rem;
    border-radius: 12px;
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# =========================
# BOTÓN ACTUALIZAR
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
def normalizar_formato(valor):
    if pd.isna(valor):
        return valor
    txt = str(valor).strip().upper()
    txt = txt.replace("[", "").replace("]", "").replace("CC", "").strip()
    txt = txt.replace(".", "").replace(",", "")
    if "2000" in txt:
        return "2.000 CC"
    if "2500" in txt:
        return "2.500 CC"
    return str(valor).strip()

def obtener_tulipas_por_formato(formato):
    if formato == "2.000 CC":
        return [7, 8, 9, 4, 5, 6, 1, 2, 3]
    if formato == "2.500 CC":
        return [5, 6, 3, 4, 1, 2]
    return []

def formatear_fecha(fecha):
    if pd.isna(fecha):
        return "-"
    return pd.to_datetime(fecha).strftime("%d-%m-%Y")

def top_valor(df, columna):
    if columna not in df.columns or df[columna].dropna().empty:
        return "-"
    return df[columna].value_counts().index[0]

def top_tabla(df, columna, nombre, top_n=10):
    if columna not in df.columns:
        return pd.DataFrame(columns=[nombre, "Frecuencia"])
    out = df[columna].value_counts().reset_index()
    out.columns = [nombre, "Frecuencia"]
    return out.head(top_n)

def mostrar_tabla_coloreada(df_tabla, subset_cols=None):
    if df_tabla is None or df_tabla.empty:
        st.info("Sin datos para mostrar.")
        return
    subset_cols = subset_cols or []
    try:
        import matplotlib  # noqa
        st.dataframe(
            df_tabla.style.background_gradient(cmap="YlOrRd", subset=subset_cols),
            use_container_width=True
        )
    except Exception:
        st.dataframe(df_tabla, use_container_width=True)

def construir_matriz_formato(df_base, equipo, formato):
    tulipas = obtener_tulipas_por_formato(formato)
    cabezales = list(range(1, 8))
    filas = []

    for tulipa in tulipas:
        fila = {"N° TULIPA": tulipa}
        for cabezal in cabezales:
            freq = df_base[
                (df_base["EQUIPO"] == equipo) &
                (df_base["FORMATO_STD"] == formato) &
                (df_base["N° CABEZAL"] == cabezal) &
                (df_base["N° TULIPA"] == tulipa)
            ].shape[0]
            fila[f"Cabezal {cabezal}"] = freq
        filas.append(fila)

    matriz = pd.DataFrame(filas)
    if not matriz.empty:
        matriz = matriz.sort_values("N° TULIPA", ascending=False).reset_index(drop=True)
    return matriz

def crear_heatmap_formato(df_base, equipo, formato):
    matriz = construir_matriz_formato(df_base, equipo, formato)
    if matriz.empty:
        return None, matriz

    columnas_cabezal = [c for c in matriz.columns if c.startswith("Cabezal ")]
    z = matriz[columnas_cabezal].values
    y = matriz["N° TULIPA"].astype(str).tolist()
    x = [c.replace("Cabezal ", "C") for c in columnas_cabezal]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            text=z,
            texttemplate="%{text}",
            colorscale="YlOrRd",
            colorbar_title="Frecuencia",
            hovertemplate="Cabezal %{x}<br>Tulipa %{y}<br>Frecuencia %{z}<extra></extra>"
        )
    )

    fig.update_layout(
        title=f"{equipo} | {formato}",
        xaxis_title="Cabezal",
        yaxis_title="Tulipa",
        height=360,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    return fig, matriz

def obtener_combo_critico(df_filtrado):
    req = ["EQUIPO", "FORMATO_STD", "N° CABEZAL", "N° TULIPA"]
    if not all(c in df_filtrado.columns for c in req):
        return None, None

    base = df_filtrado.dropna(subset=req).copy()
    if base.empty:
        return None, None

    ranking = (
        base.groupby(["EQUIPO", "FORMATO_STD", "N° CABEZAL", "N° TULIPA"])
        .size()
        .reset_index(name="Frecuencia")
        .sort_values(
            ["Frecuencia", "EQUIPO", "FORMATO_STD", "N° CABEZAL", "N° TULIPA"],
            ascending=[False, True, True, True, True]
        )
        .reset_index(drop=True)
    )

    return ranking.iloc[0], ranking

@st.cache_data(ttl=10)
def cargar_datos():
    df = pd.read_csv(URL)

    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed", na=False)]
    df = df.dropna(how="all")

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()

    df = df.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaN": pd.NA})

    if "FORMATO" in df.columns:
        df["FORMATO_STD"] = df["FORMATO"].apply(normalizar_formato)
    else:
        df["FORMATO_STD"] = pd.NA

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

    df_filtrado = df.copy()

    if "FECHA_DT" in df_filtrado.columns and not df_filtrado["FECHA_DT"].dropna().empty:
        fecha_min = df_filtrado["FECHA_DT"].min().date()
        fecha_max = df_filtrado["FECHA_DT"].max().date()

        rango_fechas = st.sidebar.date_input(
            "Rango de fechas",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max
        )

        if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
            fecha_inicio, fecha_fin = rango_fechas
            df_filtrado = df_filtrado[
                df_filtrado["FECHA_DT"].between(pd.to_datetime(fecha_inicio), pd.to_datetime(fecha_fin))
            ]

    def multiselect_col(nombre, label=None):
        if nombre in df_filtrado.columns:
            vals = sorted([v for v in df_filtrado[nombre].dropna().unique()])
            return st.sidebar.multiselect(label or nombre, vals, default=vals)
        return []

    turnos = multiselect_col("TURNO")
    operadores = multiselect_col("OPERADOR")
    equipos = multiselect_col("EQUIPO")
    formatos = multiselect_col("FORMATO_STD", "FORMATO")
    sabores = multiselect_col("SABOR")
    mantenciones = multiselect_col("MANTENCIÓN")
    observaciones = multiselect_col("OBSERVACIÓN")

    if "TURNO" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["TURNO"].isin(turnos)]
    if "OPERADOR" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["OPERADOR"].isin(operadores)]
    if "EQUIPO" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["EQUIPO"].isin(equipos)]
    if "FORMATO_STD" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["FORMATO_STD"].isin(formatos)]
    if "SABOR" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["SABOR"].isin(sabores)]
    if "MANTENCIÓN" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["MANTENCIÓN"].isin(mantenciones)]
    if "OBSERVACIÓN" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["OBSERVACIÓN"].isin(observaciones)]

    return df_filtrado

# =========================
# CARGA
# =========================
df = cargar_datos()
df_filtrado = aplicar_filtros(df)

# =========================
# KPIs
# =========================
total_mant = len(df_filtrado)
mant_top = top_valor(df_filtrado, "MANTENCIÓN")
fecha_inicio = df_filtrado["FECHA_DT"].min() if "FECHA_DT" in df_filtrado.columns and not df_filtrado.empty else pd.NaT
fecha_fin = df_filtrado["FECHA_DT"].max() if "FECHA_DT" in df_filtrado.columns and not df_filtrado.empty else pd.NaT
combo_critico, ranking_combo = obtener_combo_critico(df_filtrado)

# =========================
# HEADER
# =========================
st.title("Dashboard de Mantenciones")
st.caption("Registro de mantenciones de tulipas, encajonadora y desencajonadora")
st.markdown("**Elaborado por:** Enrique Brun  \n**Jefe de Operaciones:** Gaston Flores")

# =========================
# RESUMEN EJECUTIVO
# =========================
st.markdown('<div class="seccion">', unsafe_allow_html=True)
st.subheader("Resumen ejecutivo")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Mantenciones", total_mant)
k2.metric("Mantención más frecuente", mant_top)
k3.metric("Fecha inicio", formatear_fecha(fecha_inicio))
k4.metric("Fecha fin", formatear_fecha(fecha_fin))

if combo_critico is not None:
    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Equipo más crítico", str(combo_critico["EQUIPO"]))
    k6.metric("Formato más crítico", str(combo_critico["FORMATO_STD"]))
    k7.metric("Cabezal más crítico", int(combo_critico["N° CABEZAL"]))
    k8.metric("Tulipa más crítica", int(combo_critico["N° TULIPA"]))

    st.info(
        f"Combinación más crítica detectada: {combo_critico['EQUIPO']} | {combo_critico['FORMATO_STD']} | "
        f"Cabezal {int(combo_critico['N° CABEZAL'])} | Tulipa {int(combo_critico['N° TULIPA'])} | "
        f"Frecuencia = {int(combo_critico['Frecuencia'])}"
    )
else:
    st.warning("No hay datos suficientes para calcular criticidad.")
st.markdown("</div>", unsafe_allow_html=True)

# =========================
# ESQUEMAS AL INICIO
# =========================
st.markdown('<div class="seccion">', unsafe_allow_html=True)
st.subheader("Esquema visual de equipos")
st.caption("Se muestran 4 diagramas: 2 formatos por ENCAJONADORA y 2 formatos por DESENCAJONADORA.")

c1, c2 = st.columns(2)
with c1:
    fig, matriz = crear_heatmap_formato(df_filtrado, "ENCAJONADORA", "2.000 CC")
    if fig:
        st.plotly_chart(fig, use_container_width=True)
        mostrar_tabla_coloreada(matriz, [c for c in matriz.columns if c.startswith("Cabezal ")])
    else:
        st.info("Sin datos para ENCAJONADORA 2.000 CC")

with c2:
    fig, matriz = crear_heatmap_formato(df_filtrado, "ENCAJONADORA", "2.500 CC")
    if fig:
        st.plotly_chart(fig, use_container_width=True)
        mostrar_tabla_coloreada(matriz, [c for c in matriz.columns if c.startswith("Cabezal ")])
    else:
        st.info("Sin datos para ENCAJONADORA 2.500 CC")

c3, c4 = st.columns(2)
with c3:
    fig, matriz = crear_heatmap_formato(df_filtrado, "DESENCAJONADORA", "2.000 CC")
    if fig:
        st.plotly_chart(fig, use_container_width=True)
        mostrar_tabla_coloreada(matriz, [c for c in matriz.columns if c.startswith("Cabezal ")])
    else:
        st.info("Sin datos para DESENCAJONADORA 2.000 CC")

with c4:
    fig, matriz = crear_heatmap_formato(df_filtrado, "DESENCAJONADORA", "2.500 CC")
    if fig:
        st.plotly_chart(fig, use_container_width=True)
        mostrar_tabla_coloreada(matriz, [c for c in matriz.columns if c.startswith("Cabezal ")])
    else:
        st.info("Sin datos para DESENCAJONADORA 2.500 CC")

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# TOPS
# =========================
st.markdown('<div class="seccion">', unsafe_allow_html=True)
st.subheader("Top equipo, formato, cabezal y tulipa con mayor frecuencia")

t1, t2, t3, t4 = st.columns(4)
with t1:
    st.dataframe(top_tabla(df_filtrado, "EQUIPO", "EQUIPO"), use_container_width=True)
with t2:
    st.dataframe(top_tabla(df_filtrado, "FORMATO_STD", "FORMATO"), use_container_width=True)
with t3:
    st.dataframe(top_tabla(df_filtrado, "N° CABEZAL", "N° CABEZAL"), use_container_width=True)
with t4:
    st.dataframe(top_tabla(df_filtrado, "N° TULIPA", "N° TULIPA"), use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# =========================
# GRÁFICOS PRINCIPALES
# =========================
st.markdown('<div class="seccion">', unsafe_allow_html=True)
st.subheader("Análisis general")

g1, g2 = st.columns(2)
with g1:
    if "FECHA_DT" in df_filtrado.columns and not df_filtrado["FECHA_DT"].dropna().empty:
        serie = (
            df_filtrado.groupby("FECHA_DT")
            .size()
            .reset_index(name="Cantidad")
            .sort_values("FECHA_DT")
        )
        fig = px.line(serie, x="FECHA_DT", y="Cantidad", markers=True, title="Mantenciones por fecha")
        st.plotly_chart(fig, use_container_width=True)

with g2:
    if "MANTENCIÓN" in df_filtrado.columns:
        mant = df_filtrado["MANTENCIÓN"].value_counts().reset_index()
        mant.columns = ["MANTENCIÓN", "Cantidad"]
        fig = px.bar(mant, x="MANTENCIÓN", y="Cantidad", title="Frecuencia por tipo de mantención")
        st.plotly_chart(fig, use_container_width=True)

g3, g4 = st.columns(2)
with g3:
    if "OPERADOR" in df_filtrado.columns:
        op = df_filtrado["OPERADOR"].value_counts().reset_index()
        op.columns = ["OPERADOR", "Cantidad"]
        fig = px.bar(op, x="OPERADOR", y="Cantidad", title="Mantenciones por operador")
        st.plotly_chart(fig, use_container_width=True)

with g4:
    if "EQUIPO" in df_filtrado.columns:
        eq = df_filtrado["EQUIPO"].value_counts().reset_index()
        eq.columns = ["EQUIPO", "Cantidad"]
        fig = px.pie(eq, names="EQUIPO", values="Cantidad", title="Distribución por equipo")
        st.plotly_chart(fig, use_container_width=True)

g5, g6 = st.columns(2)
with g5:
    if "TURNO" in df_filtrado.columns:
        turno = df_filtrado["TURNO"].value_counts().reset_index()
        turno.columns = ["TURNO", "Cantidad"]
        fig = px.bar(turno, x="TURNO", y="Cantidad", title="Mantenciones por turno")
        st.plotly_chart(fig, use_container_width=True)

with g6:
    if "FORMATO_STD" in df_filtrado.columns:
        formato = df_filtrado["FORMATO_STD"].value_counts().reset_index()
        formato.columns = ["FORMATO", "Cantidad"]
        fig = px.bar(formato, x="FORMATO", y="Cantidad", title="Mantenciones por formato")
        st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# =========================
# FECHAS Y CRUCE
# =========================
f1, f2 = st.columns(2)

with f1:
    st.markdown('<div class="seccion">', unsafe_allow_html=True)
    st.subheader("¿En qué fechas se hizo mantención?")
    if "FECHA_DT" in df_filtrado.columns and not df_filtrado["FECHA_DT"].dropna().empty:
        fechas_mant = (
            df_filtrado.groupby("FECHA_DT")
            .size()
            .reset_index(name="Cantidad")
            .sort_values("FECHA_DT")
        )
        fechas_mant["FECHA"] = fechas_mant["FECHA_DT"].dt.strftime("%d-%m-%Y")
        st.dataframe(fechas_mant[["FECHA", "Cantidad"]], use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with f2:
    st.markdown('<div class="seccion">', unsafe_allow_html=True)
    st.subheader("Cruce equipo vs mantención")
    if {"EQUIPO", "MANTENCIÓN"}.issubset(df_filtrado.columns):
        tabla_cruce = pd.crosstab(df_filtrado["EQUIPO"], df_filtrado["MANTENCIÓN"])
        st.dataframe(tabla_cruce, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# TABLA DE FRECUENCIAS
# =========================
st.markdown('<div class="seccion">', unsafe_allow_html=True)
st.subheader("Tabla de frecuencia por equipo, formato, cabezal y tulipa")

if {"EQUIPO", "FORMATO_STD", "N° CABEZAL", "N° TULIPA"}.issubset(df_filtrado.columns):
    tabla_frecuencia = (
        df_filtrado.groupby(["EQUIPO", "FORMATO_STD", "N° CABEZAL", "N° TULIPA"])
        .size()
        .reset_index(name="Frecuencia")
        .sort_values(["EQUIPO", "FORMATO_STD", "N° CABEZAL", "N° TULIPA"])
    )
    mostrar_tabla_coloreada(tabla_frecuencia, ["Frecuencia"])
st.markdown("</div>", unsafe_allow_html=True)

# =========================
# TOP COMBINACIONES
# =========================
st.markdown('<div class="seccion">', unsafe_allow_html=True)
st.subheader("Top combinaciones críticas")
if ranking_combo is not None and not ranking_combo.empty:
    st.dataframe(ranking_combo.head(15), use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# =========================
# DETALLE
# =========================
st.markdown('<div class="seccion">', unsafe_allow_html=True)
st.subheader("Detalle de registros")
columnas_mostrar = [
    c for c in [
        "FECHA", "TURNO", "OPERADOR", "EQUIPO", "FORMATO_STD", "SABOR",
        "N° CABEZAL", "N° TULIPA", "MANTENCIÓN", "OBSERVACIÓN"
    ] if c in df_filtrado.columns
]
detalle = df_filtrado[columnas_mostrar].copy()
if "FORMATO_STD" in detalle.columns:
    detalle = detalle.rename(columns={"FORMATO_STD": "FORMATO"})
st.dataframe(detalle, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# =========================
# DESCARGAS
# =========================
st.subheader("Descargas")

csv_filtrado = df_filtrado.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Descargar datos filtrados en CSV",
    data=csv_filtrado,
    file_name="mantenciones_filtradas.csv",
    mime="text/csv"
)

if "tabla_frecuencia" in locals():
    csv_freq = tabla_frecuencia.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Descargar tabla de frecuencia",
        data=csv_freq,
        file_name="frecuencia_equipo_formato_cabezal_tulipa.csv",
        mime="text/csv"
    )