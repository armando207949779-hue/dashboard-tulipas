# Dashboard de mantenciones de tulipas / encajonadora-desencajonadora
# ELABORADO POR: ENRIQUE BRUN
# JEFE DE OPERACIONES: GASTON FLORES

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
# BOTÓN ACTUALIZAR DATOS
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
    df = pd.read_csv(URL)

    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed", na=False)]
    df = df.dropna(how="all")

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()

    df = df.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaN": pd.NA})

    if "FECHA" in df.columns:
        fecha_limpia = (
            df["FECHA"]
            .astype(str)
            .str.lower()
            .str.replace(r"^[^,]+,\\s*", "", regex=True)
            .str.replace(r"\\s+de\\s+", " ", regex=True)
            .str.strip()
        )

        meses = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
            "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
        }

        for mes, num in meses.items():
            fecha_limpia = fecha_limpia.str.replace(fr"\\b{mes}\\b", num, regex=True)

        df["FECHA_DT"] = pd.to_datetime(fecha_limpia, format="%d %m %Y", errors="coerce")

    for col in ["N° CABEZAL", "N° TULIPA"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

# NUEVAS FUNCIONES PARA DIAGRAMAS
def obtener_tulipas_por_formato(formato):
    if pd.isna(formato) or "2000" in str(formato).upper():
        return [7,8,9,4,5,6,1,2,3]
    elif "2500" in str(formato).upper():
        return [5,6,3,4,1,2]
    return []

def crear_matriz_heatmaps(df_filtrado):
    equipos = ["ENCAJONADORA", "DESENCAJONADORA"]
    formatos = ["2.000 CC", "2.500 CC"]
    heatmaps = {}
    
    for equipo in equipos:
        for formato in formatos:
            tulipas = obtener_tulipas_por_formato(formato)
            if not tulipas:
                continue
                
            matriz = []
            for tulipa in tulipas:
                fila = {"TULIPA": tulipa}
                for cabezal in range(1, 8):
                    count = len(df_filtrado[
                        (df_filtrado["EQUIPO"] == equipo) &
                        (df_filtrado["FORMATO"].str.contains(formato, na=False)) &
                        (df_filtrado["N° CABEZAL"] == cabezal) &
                        (df_filtrado["N° TULIPA"] == tulipa)
                    ])
                    fila[f"C{cabezal}"] = count
                matriz.append(fila)
            
            heatmaps[f"{equipo}_{formato}"] = pd.DataFrame(matriz)
    
    return heatmaps

def mostrar_diagramas(df_filtrado):
    st.subheader("📊 ESQUEMAS DE EQUIPOS - 4 DIAGRAMAS")
    heatmaps = crear_matriz_heatmaps(df_filtrado)
    
    for key, matriz in heatmaps.items():
        equipo, formato = key.split("_")
        st.markdown(f"### **{equipo} - {formato}**")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if not matriz.empty:
                fig = go.Figure(data=go.Heatmap(
                    z=matriz[[f"C{i}" for i in range(1,8)]].values,
                    x=[f"C{i}" for i in range(1,8)],
                    y=matriz["TULIPA"].astype(str),
                    text=matriz[[f"C{i}" for i in range(1,8)]].values,
                    texttemplate="%{text}",
                    colorscale="YlOrRd",
                    hoverongaps=False
                ))
                fig.update_layout(
                    title=f"Frecuencia mantenciones {equipo}-{formato}",
                    xaxis_title="Cabezales",
                    yaxis_title="Tulipas"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.dataframe(matriz.style.background_gradient(cmap="YlOrRd"))

def aplicar_filtros(df):
    st.sidebar.header("🔍 FILTROS COMPLETOS")

    # FILTRO FECHA
    if "FECHA_DT" in df.columns and not df["FECHA_DT"].dropna().empty:
        fecha_min = df["FECHA_DT"].min().date()
        fecha_max = df["FECHA_DT"].max().date()
        fecha_range = st.sidebar.date_input("Rango Fecha", (fecha_min, fecha_max))
        if len(fecha_range) == 2:
            df = df[df["FECHA_DT"].dt.date.between(fecha_range[0], fecha_range[1])]

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
    observaciones = multiselect_col("OBSERVACIÓN")

    df_filtrado = df.copy()

    if turnos: df_filtrado = df_filtrado[df_filtrado["TURNO"].isin(turnos)]
    if operadores: df_filtrado = df_filtrado[df_filtrado["OPERADOR"].isin(operadores)]
    if equipos: df_filtrado = df_filtrado[df_filtrado["EQUIPO"].isin(equipos)]
    if formatos: df_filtrado = df_filtrado[df_filtrado["FORMATO"].isin(formatos)]
    if sabores: df_filtrado = df_filtrado[df_filtrado["SABOR"].isin(sabores)]
    if mantenciones: df_filtrado = df_filtrado[df_filtrado["MANTENCIÓN"].isin(mantenciones)]
    if observaciones: df_filtrado = df_filtrado[df_filtrado["OBSERVACIÓN"].isin(observaciones)]

    return df_filtrado

def obtener_criticidad(df_filtrado):
    cols_req = ["N° CABEZAL", "N° TULIPA", "EQUIPO", "FORMATO"]
    if not all(c in df_filtrado.columns for c in cols_req):
        return None, None, None, None

    base = df_filtrado.dropna(subset=["N° CABEZAL", "N° TULIPA"]).copy()
    if base.empty:
        return None, None, None, None

    ranking_cabezal = base.groupby("N° CABEZAL").size().reset_index(name="Frecuencia").sort_values(["Frecuencia", "N° CABEZAL"], ascending=[False, True])
    ranking_tulipa = base.groupby("N° TULIPA").size().reset_index(name="Frecuencia").sort_values(["Frecuencia", "N° TULIPA"], ascending=[False, True])
    ranking_combo = base.groupby(["N° CABEZAL", "N° TULIPA", "EQUIPO", "FORMATO"]).size().reset_index(name="Frecuencia").sort_values(["Frecuencia", "N° CABEZAL", "N° TULIPA"], ascending=[False, True, True])

    cabezal_critico = ranking_cabezal.iloc[0] if not ranking_cabezal.empty else None
    tulipa_critica = ranking_tulipa.iloc[0] if not ranking_tulipa.empty else None
    combo_critico = ranking_combo.iloc[0] if not ranking_combo.empty else None

    return cabezal_critico, tulipa_critica, combo_critico, ranking_combo

# =========================
# CARGA
# =========================
df = cargar_datos()
df_filtrado = aplicar_filtros(df)

# =========================
# HEADER
# =========================
st.title("🚀 Dashboard de Mantenciones")
st.caption("Registro de mantenciones de tulipas, encajonadora y desencajonadora")
st.markdown("**ELABORADO POR: ENRIQUE BRUN**")
st.markdown("**JEFE DE OPERACIONES: GASTON FLORES**")

# =========================
# RESPUESTAS AUTOMÁTICAS - KPIs
# =========================
st.markdown("---")
st.subheader("📊 RESPUESTAS AUTOMÁTICAS")

total_mant = len(df_filtrado)
n_operadores = df_filtrado["OPERADOR"].nunique() if "OPERADOR" in df_filtrado.columns else 0
n_equipos = df_filtrado["EQUIPO"].nunique() if "EQUIPO" in df_filtrado.columns else 0
mant_top = df_filtrado["MANTENCIÓN"].mode().iloc[0] if "MANTENCIÓN" in df_filtrado.columns and not df_filtrado["MANTENCIÓN"].dropna().empty else "-"
fecha_inicio = df_filtrado["FECHA"].min() if "FECHA" in df_filtrado.columns else "-"
fecha_fin = df_filtrado["FECHA"].max() if "FECHA" in df_filtrado.columns else "-"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("¿Cuántas mantenciones hubo?", total_mant)
c2.metric("¿Mantención más frecuente?", mant_top)
c3.metric("¿Fecha inicio?", fecha_inicio)
c4.metric("¿Fecha fin?", fecha_fin)
c5.metric("Registros filtrados", len(df_filtrado))

# =========================
# CRITICIDAD
# =========================
cabezal_critico, tulipa_critica, combo_critico, ranking_combo = obtener_criticidad(df_filtrado)

st.subheader("🎯 ¿CUÁL ES EL FORMATO, EQUIPO, CABEZAL, TULIPA MÁS CRÍTICO?")
if combo_critico is not None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Equipo CRÍTICO", combo_critico["EQUIPO"])
    col2.metric("Formato CRÍTICO", combo_critico["FORMATO"])
    col3.metric("Cabezal CRÍTICO", int(combo_critico["N° CABEZAL"]))
    col4.metric("Tulipa CRÍTICA", int(combo_critico["N° TULIPA"]))
    
    st.success(f"**🚨 COMBINACIÓN MÁS CRÍTICA:** {combo_critico['EQUIPO']} | {combo_critico['FORMATO']} | Cabezal {int(combo_critico['N° CABEZAL'])} | Tulipa {int(combo_critico['N° TULIPA'])} (Frecuencia: {int(combo_critico['Frecuencia'])})")
else:
    st.warning("No hay datos suficientes para criticidad")

# =========================
# TOP FRECUENCIAS
# =========================
st.subheader("🏆 TOP con mayor frecuencia")
col_t1, col_t2, col_t3, col_t4 = st.columns(4)
with col_t1: st.dataframe(df_filtrado["EQUIPO"].value_counts().reset_index(), use_container_width=True)
with col_t2: st.dataframe(df_filtrado["FORMATO"].value_counts().reset_index(), use_container_width=True)
with col_t3: st.dataframe(df_filtrado["N° CABEZAL"].value_counts().reset_index(), use_container_width=True)
with col_t4: st.dataframe(df_filtrado["N° TULIPA"].value_counts().reset_index(), use_container_width=True)

# =========================
# GRÁFICOS ORIGINALES
# =========================
st.markdown("---")
st.subheader("📈 GRÁFICOS")

col1, col2 = st.columns(2)
with col1:
    if "FECHA_DT" in df_filtrado.columns and not df_filtrado["FECHA_DT"].dropna().empty:
        serie = df_filtrado.groupby("FECHA_DT").size().reset_index(name="Cantidad").sort_values("FECHA_DT")
        fig = px.line(serie, x="FECHA_DT", y="Cantidad", markers=True, title="¿En qué fechas se hizo mantención?")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if "MANTENCIÓN" in df_filtrado.columns:
        mant = df_filtrado["MANTENCIÓN"].value_counts().reset_index()
        mant.columns = ["MANTENCIÓN", "Cantidad"]
        fig = px.bar(mant, x="MANTENCIÓN", y="Cantidad", title="Frecuencia por tipo de mantención")
        st.plotly_chart(fig, use_container_width=True)

# Más gráficos
col3, col4 = st.columns(2)
with col3:
    if "OPERADOR" in df_filtrado.columns:
        op = df_filtrado["OPERADOR"].value_counts().reset_index()
        op.columns = ["OPERADOR", "Cantidad"]
        fig = px.bar(op, x="OPERADOR", y="Cantidad", title="Mantenciones por operador")
        st.plotly_chart(fig, use_container_width=True)

with col4:
    if "EQUIPO" in df_filtrado.columns:
        eq = df_filtrado["EQUIPO"].value_counts().reset_index()
        eq.columns = ["EQUIPO", "Cantidad"]
        fig = px.pie(eq, names="EQUIPO", values="Cantidad", title="Distribución por equipo")
        st.plotly_chart(fig, use_container_width=True)

col5, col6 = st.columns(2)
with col5:
    if "TURNO" in df_filtrado.columns:
        turno = df_filtrado["TURNO"].value_counts().reset_index()
        turno.columns = ["TURNO", "Cantidad"]
        fig = px.bar(turno, x="TURNO", y="Cantidad", title="Mantenciones por turno")
        st.plotly_chart(fig, use_container_width=True)

with col6:
    if "FORMATO" in df_filtrado.columns:
        formato = df_filtrado["FORMATO"].value_counts().reset_index()
        formato.columns = ["FORMATO", "Cantidad"]
        fig = px.bar(formato, x="FORMATO", y="Cantidad", title="Mantenciones por formato")
        st.plotly_chart(fig, use_container_width=True)

# =========================
# 4 DIAGRAMAS PRINCIPALES
# =========================
mostrar_diagramas(df_filtrado)

# =========================
# ANÁLISIS ADICIONAL
# =========================
st.markdown("---")
st.subheader("📊 CRUCE EQUIPO VS MANTENCIÓN")
if {"EQUIPO", "MANTENCIÓN"}.issubset(df_filtrado.columns):
    tabla_cruce = pd.crosstab(df_filtrado["EQUIPO"], df_filtrado["MANTENCIÓN"])
    st.dataframe(tabla_cruce.style.background_gradient(cmap="YlOrRd"), use_container_width=True)

st.subheader("📋 DETALLE DE REGISTROS")
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