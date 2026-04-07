# Dashboard de mantenciones de tulipas / encajonadora-desencajonadora
# Elaborado por: Enrique Brun
# Jefe de Operaciones: Gaston Flores
# VERSIÓN CORREGIDA - Manejo robusto de datos vacíos

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
# FUNCIONES AUXILIARES ROBUSTAS
# =========================
def safe_value_counts(df, col, top_n=10):
    """Value counts seguro para datos vacíos"""
    if col not in df.columns or df[col].dropna().empty:
        return pd.DataFrame(columns=[col, "Frecuencia"])
    vc = df[col].value_counts().head(top_n).reset_index()
    vc.columns = [col, "Frecuencia"]
    return vc

def safe_groupby_count(df, group_col, date_col=None):
    """Groupby seguro con manejo de fechas"""
    if df.empty or group_col not in df.columns:
        return pd.DataFrame()
    
    if date_col and date_col in df.columns:
        try:
            df_valid = df.dropna(subset=[date_col])
            if df_valid.empty:
                return pd.DataFrame()
            grouped = df_valid.groupby(df_valid[date_col].dt.date).size().reset_index(name="Cantidad")
            grouped["FECHA"] = grouped[date_col].astype(str)
            return grouped[["FECHA", "Cantidad"]].sort_values("FECHA")
        except:
            # Fallback sin fechas
            pass
    
    return safe_value_counts(df, group_col)

def normalizar_formato(valor):
    if pd.isna(valor):
        return "SIN FORMATO"
    txt = str(valor).strip().upper()
    txt = txt.replace("[", "").replace("]", "").replace("CC", "").strip()
    txt = txt.replace(".", "").replace(",", "")
    if "2000" in txt:
        return "2.000 CC"
    if "2500" in txt:
        return "2.500 CC"
    return str(valor).strip() or "SIN FORMATO"

def obtener_tulipas_por_formato(formato):
    if "2.000" in str(formato):
        return [7,8,9,4,5,6,1,2,3]
    if "2.500" in str(formato):
        return [5,6,3,4,1,2]
    return []

def construir_matriz_formato(df_base, equipo, formato):
    if df_base.empty:
        return pd.DataFrame()
    
    tulipas = obtener_tulipas_por_formato(formato)
    if not tulipas:
        return pd.DataFrame()
    
    cabezales = list(range(1, 8))
    filas = []
    
    for tulipa in tulipas:
        fila = {"N° TULIPA": tulipa}
        for cabezal in cabezales:
            mask = (
                (df_base["EQUIPO"] == equipo) &
                (df_base["FORMATO_STD"] == formato) &
                (df_base["N° CABEZAL"] == cabezal) &
                (df_base["N° TULIPA"] == tulipa)
            )
            freq = df_base[mask].shape[0]
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
    if not columnas_cabezal:
        return None, matriz
        
    z = matriz[columnas_cabezal].values
    y = matriz["N° TULIPA"].astype(str).tolist()
    x = [c.replace("Cabezal ", "C") for c in columnas_cabezal]
    
    fig = go.Figure(data=go.Heatmap(
        z=z, x=x, y=y, text=z, texttemplate="%{text}",
        colorscale="YlOrRd", colorbar_title="Frecuencia",
        hovertemplate="Cabezal %{x}<br>Tulipa %{y}<br>Frecuencia %{z}<extra></extra>"
    ))
    
    fig.update_layout(
        title=f"{equipo} - {formato}",
        xaxis_title="Cabezal", yaxis_title="Tulipa",
        height=400, margin={"t": 50, "b": 50}
    )
    return fig, matriz

def formatear_fecha(fecha):
    try:
        if pd.isna(fecha):
            return "-"
        return pd.to_datetime(fecha).strftime("%d-%m-%Y")
    except:
        return "-"

def obtener_combo_critico(df_filtrado):
    req = ["EQUIPO", "FORMATO_STD", "N° CABEZAL", "N° TULIPA"]
    if df_filtrado.empty or not all(c in df_filtrado.columns for c in req):
        return None, pd.DataFrame()
    
    base = df_filtrado.dropna(subset=req)
    if base.empty:
        return None, pd.DataFrame()
    
    ranking = (
        base.groupby(["EQUIPO", "FORMATO_STD", "N° CABEZAL", "N° TULIPA"])
        .size()
        .reset_index(name="Frecuencia")
        .sort_values(["Frecuencia", "EQUIPO", "FORMATO_STD"], ascending=[False, True, True])
    )
    
    return ranking.iloc[0] if not ranking.empty else None, ranking

# =========================
# CARGA DE DATOS ROBUSTA
# =========================
@st.cache_data(ttl=30)
def cargar_datos():
    try:
        df = pd.read_csv(URL)
        if df.empty:
            st.warning("❌ No se pudieron cargar datos del Google Sheet")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error cargando datos: {e}")
        return pd.DataFrame()
    
    # Limpieza robusta
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed", na=False)]
    df = df.dropna(how="all")
    
    if df.empty:
        return df
    
    # Normalizar columnas
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()
    
    df = df.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaN": pd.NA})
    
    # Formato estándar
    if "FORMATO" in df.columns:
        df["FORMATO_STD"] = df["FORMATO"].apply(normalizar_formato)
    
    # Parseo de fecha robusto
    if "FECHA" in df.columns:
        try:
            fecha_limpia = df["FECHA"].astype(str).str.lower()
            fecha_limpia = fecha_limpia.str.replace(r"^[^,]+,\s*", "", regex=True)
            fecha_limpia = fecha_limpia.str.replace(r"\s+de\s+", " ", regex=True).str.strip()
            
            meses = {
                "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
                "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
                "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
            }
            
            for mes, num in meses.items():
                fecha_limpia = fecha_limpia.str.replace(fr"\b{mes}\b", num, regex=True)
            
            df["FECHA_DT"] = pd.to_datetime(fecha_limpia, format="%d %m %Y", errors="coerce")
        except Exception as e:
            st.warning(f"Advertencia parseando fechas: {e}")
            df["FECHA_DT"] = pd.NaT
    
    # Numéricos
    for col in ["N° CABEZAL", "N° TULIPA"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    st.success(f"✅ Datos cargados: {len(df)} registros")
    return df

# =========================
# FILTROS MEJORADOS CON VALIDACIÓN
# =========================
def aplicar_filtros(df):
    st.sidebar.header("🔍 Filtros")
    
    if df.empty:
        st.sidebar.warning("No hay datos base para filtrar")
        return df
    
    df_filtrado = df.copy()
    
    # Filtro fecha robusto
    if "FECHA_DT" in df_filtrado.columns:
        fechas_validas = df_filtrado["FECHA_DT"].dropna()
        if not fechas_validas.empty:
            fecha_min = fechas_validas.min().date()
            fecha_max = fechas_validas.max().date()
            
            col_f1, col_f2 = st.sidebar.columns(2)
            with col_f1:
                fecha_inicio = st.date_input("Desde", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
            with col_f2:
                fecha_fin = st.date_input("Hasta", value=fecha_max, min_value=fecha_min, max_value=fecha_max)
            
            mask_fecha = df_filtrado["FECHA_DT"].between(
                pd.to_datetime(fecha_inicio), pd.to_datetime(fecha_fin)
            )
            df_filtrado = df_filtrado[mask_fecha]
    
    # Multiselects seguros
    def multiselect_safe(df_f, col, label=None):
        if col not in df_f.columns:
            return []
        vals = sorted(df_f[col].dropna().unique())
        if not vals:
            return []
        default = vals[:3] if len(vals) > 3 else vals
        return st.sidebar.multiselect(label or col, vals, default=default)
    
    filtros = {
        "TURNO": multiselect_safe(df_filtrado, "TURNO"),
        "OPERADOR": multiselect_safe(df_filtrado, "OPERADOR"),
        "EQUIPO": multiselect_safe(df_filtrado, "EQUIPO"),
        "FORMATO_STD": multiselect_safe(df_filtrado, "FORMATO_STD", "FORMATO"),
        "SABOR": multiselect_safe(df_filtrado, "SABOR"),
        "MANTENCIÓN": multiselect_safe(df_filtrado, "MANTENCIÓN"),
        "OBSERVACIÓN": multiselect_safe(df_filtrado, "OBSERVACIÓN")
    }
    
    # Aplicar filtros
    for col, valores in filtros.items():
        if col in df_filtrado.columns and valores:
            df_filtrado = df_filtrado[df_filtrado[col].isin(valores)]
    
    st.sidebar.markdown(f"**Registros filtrados: {len(df_filtrado)}**")
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
st.markdown("***Elaborado por: Enrique Brun | Jefe de Operaciones: Gaston Flores***")

if df_filtrado.empty:
    st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados. Prueba:")
    st.markdown("- **Ampliar rango de fechas**")
    st.markdown("- **Seleccionar 'Select All' en filtros**")
    st.markdown("- **Presionar 'Actualizar datos'**")
    st.stop()

# =========================
# KPIs PRINCIPALES
# =========================
st.markdown("---")
st.subheader("📊 Respuestas Automáticas")

total_mant = len(df_filtrado)
mant_top = safe_value_counts(df_filtrado, "MANTENCIÓN")["MANTENCIÓN"].iloc[0] if len(safe_value_counts(df_filtrado, "MANTENCIÓN")) > 0 else "-"

fecha_inicio = df_filtrado["FECHA_DT"].min() if "FECHA_DT" in df_filtrado.columns else pd.NaT
fecha_fin = df_filtrado["FECHA_DT"].max() if "FECHA_DT" in df_filtrado.columns else pd.NaT

combo_critico, ranking_combo = obtener_combo_critico(df_filtrado)

k1, k2, k3, k4 = st.columns(4)
k1.metric("📈 Total mantenciones", total_mant)
k2.metric("🔥 Mantención más frecuente", mant_top)
k3.metric("📅 Fecha inicio", formatear_fecha(fecha_inicio))
k4.metric("📅 Fecha fin", formatear_fecha(fecha_fin))

if combo_critico is not None:
    st.success(f"""
    **🎯 COMBINACIÓN MÁS CRÍTICA:**
    **{combo_critico['EQUIPO']}** | **{combo_critico['FORMATO_STD']}** | 
    Cabezal **{int(combo_critico['N° CABEZAL'])}** | Tulipa **{int(combo_critico['N° TULIPA'])}**
    *(Frecuencia: {int(combo_critico['Frecuencia'])})**
    """)

# =========================
# TOP FRECUENCIAS
# =========================
st.subheader("🏆 TOP por Categoría")
t1, t2, t3, t4 = st.columns(4)

with t1:
    st.markdown("**Equipo**")
    eq_top = safe_value_counts(df_filtrado, "EQUIPO")
    st.dataframe(eq_top, use_container_width=True)

with t2:
    st.markdown("**Formato**")
    fmt_top = safe_value_counts(df_filtrado, "FORMATO_STD")
    st.dataframe(fmt_top.rename(columns={"FORMATO_STD": "FORMATO"}), use_container_width=True)

with t3:
    st.markdown("**Cabezal**")
    cab_top = safe_value_counts(df_filtrado, "N° CABEZAL")
    st.dataframe(cab_top, use_container_width=True)

with t4:
    st.markdown("**Tulipa**")
    tul_top = safe_value_counts(df_filtrado, "N° TULIPA")
    st.dataframe(tul_top, use_container_width=True)

# =========================
# GRÁFICOS PRINCIPALES
# =========================
col1, col2 = st.columns(2)

with col1:
    st.markdown("**📅 Evolución temporal**")
    fechas_graf = safe_groupby_count(df_filtrado, None, "FECHA_DT")
    if not fechas_graf.empty and len(fechas_graf) > 0:
        fig = px.line(fechas_graf, x="FECHA", y="Cantidad", markers=True)
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos de fecha para graficar")

with col2:
    st.markdown("**🔧 Tipos de mantención**")
    mant_graf = safe_value_counts(df_filtrado, "MANTENCIÓN", 8)
    if not mant_graf.empty:
        fig = px.bar(mant_graf, x="Cantidad", y="MANTENCIÓN", orientation='h')
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos de mantención")

# Más gráficos...
col3, col4 = st.columns(2)
with col3:
    op_graf = safe_value_counts(df_filtrado, "OPERADOR", 8)
    if not op_graf.empty:
        st.markdown("**👷 Por operador**")
        fig = px.bar(op_graf, x="Cantidad", y="OPERADOR", orientation='h')
        st.plotly_chart(fig, use_container_width=True)

with col4:
    eq_pie = safe_value_counts(df_filtrado, "EQUIPO")
    if not eq_pie.empty:
        st.markdown("**🏭 Distribución equipos**")
        fig = px.pie(eq_pie, names="EQUIPO", values="Frecuencia")
        st.plotly_chart(fig, use_container_width=True)

# =========================
# ESQUEMAS DE EQUIPOS
# =========================
st.markdown("---")
st.subheader("🔥 ESQUEMAS DE FRECUENCIA (4 Diagramas)")

equipos = ["ENCAJONADORA", "DESENCAJONADORA"]
formatos = ["2.000 CC", "2.500 CC"]

for equipo in equipos:
    st.markdown(f"### **{equipo}**")
    c1, c2 = st.columns(2)
    
    for i, formato in enumerate(formatos):
        with (c1 if i == 0 else c2):
            fig, matriz = crear_heatmap_formato(df_filtrado, equipo, formato)
            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(f"**Tabla {formato}:**")
                st.dataframe(matriz.style.background_gradient(cmap="YlOrRd", subset=[c for c in matriz.columns if "Cabezal" in c]), use_container_width=True)
            else:
                st.info(f"Sin datos para {equipo} - {formato}")

# =========================
# DESCARGAS
# =========================
st.markdown("---")
col_dl1, col_dl2 = st.columns(2)

columnas_export = ["FECHA", "TURNO", "OPERADOR", "EQUIPO", "FORMATO", "SABOR", "N° CABEZAL", "N° TULIPA", "MANTENCIÓN", "OBSERVACIÓN"]
columnas_validas = [c for c in columnas_export if c in df_filtrado.columns]

with col_dl1:
    csv_filtrado = df_filtrado[columnas_validas].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 Datos filtrados",
        csv_filtrado,
        f"mantenciones_filtradas_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        "text/csv"
    )

if not ranking_combo.empty:
    with col_dl2:
        csv_freq = ranking_combo.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📊 Frecuencias completas",
            csv_freq,
            f"frecuencias_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv"
        )

st.markdown("---")
st.caption("✅ Dashboard actualizado y robusto contra errores de datos vacíos")