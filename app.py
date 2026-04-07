# Dashboard de mantenciones de tulipas / encajonadora-desencajonadora
# Elaborado por: Enrique Brun
# Jefe de Operaciones: Gaston Flores

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

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
    if st.button("🔄 Actualizar datos"):
        st.cache_data.clear()
        st.rerun()
with col_btn2:
    st.caption("Si cambias datos en Google Sheets, presiona este botón para recargar.")

# =========================
# FUNCIONES AUXILIARES
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
        return [7,8,9,4,5,6,1,2,3]
    if formato == "2.500 CC":
        return [5,6,3,4,1,2]
    return []

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
        title=f"{equipo} - {formato}",
        xaxis_title="Cabezal",
        yaxis_title="Tulipa",
        height=420,
        margin={"t": 60, "b": 60, "l": 60, "r": 60}
    )
    return fig, matriz

def top_valor(df, columna):
    if columna not in df.columns or df[columna].dropna().empty:
        return "-"
    vc = df[columna].value_counts()
    return vc.index[0]

def top_tabla(df, columna, nombre_columna="Elemento", top_n=10):
    if columna not in df.columns:
        return pd.DataFrame(columns=[nombre_columna, "Frecuencia"])
    tabla = df[columna].value_counts().reset_index()
    tabla.columns = [nombre_columna, "Frecuencia"]
    return tabla.head(top_n)

def formatear_fecha(fecha):
    if pd.isna(fecha):
        return "-"
    return pd.to_datetime(fecha).strftime("%d-%m-%Y")

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

def mostrar_tabla_coloreada(df_tabla, subset_cols=None):
    if df_tabla is None or df_tabla.empty:
        st.info("Sin datos para mostrar.")
        return
    
    subset_cols = subset_cols or []
    
    try:
        st.dataframe(
            df_tabla.style.background_gradient(cmap="YlOrRd", subset=subset_cols),
            use_container_width=True
        )
    except Exception:
        st.dataframe(df_tabla, use_container_width=True)

# =========================
# CARGA DE DATOS
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

# =========================
# FILTROS MEJORADOS
# =========================
def aplicar_filtros(df):
    st.sidebar.header("🔍 Filtros")
    
    df_filtrado = df.copy()
    
    # Filtro de fecha mejorado
    if "FECHA_DT" in df_filtrado.columns and not df_filtrado["FECHA_DT"].dropna().empty:
        fecha_min = df_filtrado["FECHA_DT"].min().date()
        fecha_max = df_filtrado["FECHA_DT"].max().date()
        
        col_f1, col_f2 = st.sidebar.columns(2)
        with col_f1:
            fecha_inicio = st.date_input("Desde", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
        with col_f2:
            fecha_fin = st.date_input("Hasta", value=fecha_max, min_value=fecha_min, max_value=fecha_max)
        
        df_filtrado = df_filtrado[
            df_filtrado["FECHA_DT"].between(pd.to_datetime(fecha_inicio), pd.to_datetime(fecha_fin))
        ]
    
    def multiselect_col(nombre, label=None):
        if nombre in df_filtrado.columns:
            vals = sorted(df_filtrado[nombre].dropna().unique())
            if not vals:
                return []
            return st.sidebar.multiselect(label or nombre, vals, default=vals[:3] if len(vals)>3 else vals)
        return []
    
    turnos = multiselect_col("TURNO")
    operadores = multiselect_col("OPERADOR")
    equipos = multiselect_col("EQUIPO")
    formatos = multiselect_col("FORMATO_STD", "FORMATO")
    sabores = multiselect_col("SABOR")
    mantenciones = multiselect_col("MANTENCIÓN")
    observaciones = multiselect_col("OBSERVACIÓN")
    
    # Aplicar filtros
    filtros = {
        "TURNO": turnos,
        "OPERADOR": operadores, 
        "EQUIPO": equipos,
        "FORMATO_STD": formatos,
        "SABOR": sabores,
        "MANTENCIÓN": mantenciones,
        "OBSERVACIÓN": observaciones
    }
    
    for col, valores in filtros.items():
        if col in df_filtrado.columns and valores:
            df_filtrado = df_filtrado[df_filtrado[col].isin(valores)]
    
    return df_filtrado

# =========================
# CARGA PRINCIPAL
# =========================
df = cargar_datos()
df_filtrado = aplicar_filtros(df)

# =========================
# HEADER
# =========================
st.title("🚀 Dashboard de Mantenciones")
st.markdown("**Tulipas - Encajonadora y Desencajonadora**")
st.markdown("***Elaborado por: Enrique Brun* | *Jefe de Operaciones: Gaston Flores***")

# =========================
# KPIs PRINCIPALES - RESPUESTAS DIRECTAS
# =========================
st.markdown("---")
st.subheader("📊 Respuestas Automáticas")

total_mant = len(df_filtrado)
mant_top = top_valor(df_filtrado, "MANTENCIÓN")
fecha_inicio = df_filtrado["FECHA_DT"].min() if "FECHA_DT" in df_filtrado.columns and not df_filtrado.empty else pd.NaT
fecha_fin = df_filtrado["FECHA_DT"].max() if "FECHA_DT" in df_filtrado.columns and not df_filtrado.empty else pd.NaT

combo_critico, ranking_combo = obtener_combo_critico(df_filtrado)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📈 Total mantenciones", total_mant)
k2.metric("🔥 Mantención más frecuente", mant_top)
k3.metric("📅 Fecha inicio", formatear_fecha(fecha_inicio))
k4.metric("📅 Fecha fin", formatear_fecha(fecha_fin))
k5.metric("🎯 Registros filtrados", f"{len(df_filtrado)}")

if combo_critico is not None:
    st.success(f"**🎯 Combinación MÁS CRÍTICA:** {combo_critico['EQUIPO']} | {combo_critico['FORMATO_STD']} | Cabezal {int(combo_critico['N° CABEZAL'])} | Tulipa {int(combo_critico['N° TULIPA'])} (**{int(combo_critico['Frecuencia'])}** veces)")

# =========================
# TOP FRECUENCIAS
# =========================
st.subheader("🏆 TOP por Categoría")
t1, t2, t3, t4 = st.columns(4)
with t1: 
    st.markdown("**Equipo**")
    st.dataframe(top_tabla(df_filtrado, "EQUIPO"), use_container_width=True)
with t2:
    st.markdown("**Formato**") 
    st.dataframe(top_tabla(df_filtrado, "FORMATO_STD", "FORMATO"), use_container_width=True)
with t3:
    st.markdown("**Cabezal**")
    st.dataframe(top_tabla(df_filtrado, "N° CABEZAL"), use_container_width=True)
with t4:
    st.markdown("**Tulipa**")
    st.dataframe(top_tabla(df_filtrado, "N° TULIPA"), use_container_width=True)

# =========================
# GRÁFICOS PRINCIPALES
# =========================
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**📅 Evolución temporal**")
    if "FECHA_DT" in df_filtrado.columns and not df_filtrado["FECHA_DT"].dropna().empty:
        serie = df_filtrado.groupby(df_filtrado["FECHA_DT"].dt.date).size().reset_index(name="Cantidad")
        serie["FECHA"] = serie["FECHA_DT"].astype(str)
        fig = px.line(serie, x="FECHA", y="Cantidad", markers=True, title="Mantenciones por día")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("**🔧 Tipos de mantención**")
    if "MANTENCIÓN" in df_filtrado.columns:
        mant = df_filtrado["MANTENCIÓN"].value_counts().head(10).reset_index()
        mant.columns = ["MANTENCIÓN", "Cantidad"]
        fig = px.bar(mant, x="Cantidad", y="MANTENCIÓN", orientation='h', title="Frecuencia por tipo")
        st.plotly_chart(fig, use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    st.markdown("**👷 Por operador**")
    if "OPERADOR" in df_filtrado.columns:
        op = df_filtrado["OPERADOR"].value_counts().reset_index()
        op.columns = ["OPERADOR", "Cantidad"]
        fig = px.bar(op, x="Cantidad", y="OPERADOR", orientation='h')
        st.plotly_chart(fig, use_container_width=True)

with col4:
    st.markdown("**🏭 Distribución equipos**")
    if "EQUIPO" in df_filtrado.columns:
        eq = df_filtrado["EQUIPO"].value_counts().reset_index()
        eq.columns = ["EQUIPO", "Cantidad"]
        fig = px.pie(eq, names="EQUIPO", values="Cantidad")
        st.plotly_chart(fig, use_container_width=True)

# =========================
# ESQUEMAS DE EQUIPOS (4 Diagramas)
# =========================
st.markdown("---")
st.subheader("🔥 ESQUEMAS DE FRECUENCIA POR CABEZAL Y TULIPA")
st.markdown("*4 diagramas: 2 equipos × 2 formatos cada uno*")

equipos = ["ENCAJONADORA", "DESENCAJONADORA"]
formatos = ["2.000 CC", "2.500 CC"]

for equipo in equipos:
    st.markdown(f"### {equipo}")
    c1, c2 = st.columns(2)
    
    for i, formato in enumerate(formatos):
        col = c1 if i == 0 else c2
        with col:
            fig, matriz = crear_heatmap_formato(df_filtrado, equipo, formato)
            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(f"**Tabla {formato}:**")
                mostrar_tabla_coloreada(matriz)
            else:
                st.info(f"Sin datos para {equipo} - {formato}")

# =========================
# ANÁLISIS AVANZADO
# =========================
st.markdown("---")
col_a1, col_a2 = st.columns(2)

with col_a1:
    st.markdown("**⏰ Por turno**")
    if "TURNO" in df_filtrado.columns:
        turno = df_filtrado["TURNO"].value_counts().reset_index()
        turno.columns = ["TURNO", "Cantidad"]
        fig = px.bar(turno, x="TURNO", y="Cantidad", title="")
        st.plotly_chart(fig, use_container_width=True)

with col_a2:
    st.markdown("**📦 Por formato**")
    if "FORMATO_STD" in df_filtrado.columns:
        formato = df_filtrado["FORMATO_STD"].value_counts().reset_index()
        formato.columns = ["FORMATO", "Cantidad"]
        fig = px.bar(formato, x="FORMATO", y="Cantidad", title="")
        st.plotly_chart(fig, use_container_width=True)

# =========================
# CRUCES Y TABLAS
# =========================
st.subheader("📋 Análisis Cruzado")
c1, c2 = st.columns(2)

with c1:
    if {"EQUIPO", "MANTENCIÓN"}.issubset(df_filtrado.columns):
        st.markdown("**Cruce Equipo × Mantención**")
        tabla_cruce = pd.crosstab(df_filtrado["EQUIPO"], df_filtrado["MANTENCIÓN"])
        mostrar_tabla_coloreada(tabla_cruce)

with c2:
    st.markdown("**📊 Fechas con mantención**")
    if "FECHA_DT" in df_filtrado.columns:
        fechas = df_filtrado.groupby(df_filtrado["FECHA_DT"].dt.date).size().reset_index(name="Cantidad")
        fechas["FECHA"] = fechas["FECHA_DT"].dt.strftime("%d-%m-%Y")
        st.dataframe(fechas[["FECHA", "Cantidad"]].sort_values("FECHA"), use_container_width=True)

# =========================
# TABLA COMPLETA FRECUENCIAS
# =========================
st.subheader("🎯 Tabla Completa: Frecuencia por Combinación")
if {"EQUIPO", "FORMATO_STD", "N° CABEZAL", "N° TULIPA"}.issubset(df_filtrado.columns):
    tabla_frec = (
        df_filtrado.groupby(["EQUIPO", "FORMATO_STD", "N° CABEZAL", "N° TULIPA"])
        .size()
        .reset_index(name="Frecuencia")
        .sort_values("Frecuencia", ascending=False)
    )
    mostrar_tabla_coloreada(tabla_frec, subset_cols=["Frecuencia"])
    st.session_state['tabla_frec'] = tabla_frec

# =========================
# DETALLE REGISTROS
# =========================
st.markdown("---")
st.subheader("📄 Detalle Completo de Registros")
columnas_mostrar = [
    c for c in ["FECHA", "TURNO", "OPERADOR", "EQUIPO", "FORMATO", "SABOR",
                "N° CABEZAL", "N° TULIPA", "MANTENCIÓN", "OBSERVACIÓN"] 
    if c in df_filtrado.columns
]
if "FORMATO_STD" in df_filtrado.columns:
    detalle = df_filtrado.copy()
    detalle["FORMATO"] = detalle["FORMATO_STD"]
    columnas_mostrar = [c if c != "FORMATO_STD" else "FORMATO" for c in columnas_mostrar]
    st.dataframe(detalle[columnas_mostrar], use_container_width=True)
else:
    st.dataframe(df_filtrado[columnas_mostrar], use_container_width=True)

# =========================
# DESCARGAS
# =========================
st.markdown("---")
st.subheader("💾 Descargar Datos")

csv_filtrado = df_filtrado[columnas_mostrar].to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "📥 Datos filtrados (CSV)",
    data=csv_filtrado,
    file_name=f"mantenciones_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

if 'tabla_frec' in st.session_state:
    csv_freq = st.session_state['tabla_frec'].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📊 Tabla frecuencias completas (CSV)",
        data=csv_freq,
        file_name=f"frecuencias_completas_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )