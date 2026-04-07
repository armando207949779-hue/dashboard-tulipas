# Dashboard de mantenciones de tulipas / encajonadora-desencajonadora
# Elaborado por: Enrique Brun
# Jefe de Operaciones: Gaston Flores
# VERSIÓN ESTABLE - Basada en código original funcional

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
    if st.button("🔄 Actualizar datos"):
        st.cache_data.clear()
        st.rerun()
with col_btn2:
    st.caption("Si cambias datos en Google Sheets, presiona este botón para recargar.")

# =========================
# FUNCIONES AUXILIARES (ORIGINALES + MEJORAS MÍNIMAS)
# =========================
def normalizar_formato(valor):
    if pd.isna(valor):
        return valor
    txt = str(valor).strip().upper()
    txt = txt.replace("[", "").replace("]", "")
    txt = txt.replace("CC", "").strip()
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
        height=420
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

# =========================
# CARGA (ORIGINAL)
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

def aplicar_filtros(df):
    st.sidebar.header("🔍 Filtros")

    df_filtrado = df.copy()

    # Filtro fecha MEJORADO
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
            vals = sorted(df_filtrado[nombre].dropna().unique())
            return st.sidebar.multiselect(label or nombre, vals, default=vals)
        return []

    turnos = multiselect_col("TURNO")
    operadores = multiselect_col("OPERADOR")
    equipos = multiselect_col("EQUIPO")
    formatos = multiselect_col("FORMATO_STD", "FORMATO")
    sabores = multiselect_col("SABOR")
    mantenciones = multiselect_col("MANTENCIÓN")
    observaciones = multiselect_col("OBSERVACIÓN")

    if "TURNO" in df_filtrado.columns and turnos:
        df_filtrado = df_filtrado[df_filtrado["TURNO"].isin(turnos)]
    if "OPERADOR" in df_filtrado.columns and operadores:
        df_filtrado = df_filtrado[df_filtrado["OPERADOR"].isin(operadores)]
    if "EQUIPO" in df_filtrado.columns and equipos:
        df_filtrado = df_filtrado[df_filtrado["EQUIPO"].isin(equipos)]
    if "FORMATO_STD" in df_filtrado.columns and formatos:
        df_filtrado = df_filtrado[df_filtrado["FORMATO_STD"].isin(formatos)]
    if "SABOR" in df_filtrado.columns and sabores:
        df_filtrado = df_filtrado[df_filtrado["SABOR"].isin(sabores)]
    if "MANTENCIÓN" in df_filtrado.columns and mantenciones:
        df_filtrado = df_filtrado[df_filtrado["MANTENCIÓN"].isin(mantenciones)]
    if "OBSERVACIÓN" in df_filtrado.columns and observaciones:
        df_filtrado = df_filtrado[df_filtrado["OBSERVACIÓN"].isin(observaciones)]

    st.sidebar.markdown(f"**Registros: {len(df_filtrado)}**")
    return df_filtrado

# =========================
# DATA
# =========================
df = cargar_datos()
df_filtrado = aplicar_filtros(df)

if df_filtrado.empty:
    st.warning("⚠️ Sin datos con filtros actuales. Prueba: Ampliar fechas o seleccionar 'Select All'")
    st.stop()

# =========================
# HEADER
# =========================
st.title("🚀 Dashboard de Mantenciones")
st.caption("Registro de mantenciones de tulipas, encajonadora y desencajonadora")
st.markdown("**Elaborado por:** Enrique Brun  | **Jefe de Operaciones:** Gaston Flores")

# =========================
# KPIs
# =========================
total_mant = len(df_filtrado)
mant_top = top_valor(df_filtrado, "MANTENCIÓN")
fecha_inicio = df_filtrado["FECHA_DT"].min() if "FECHA_DT" in df_filtrado.columns else pd.NaT
fecha_fin = df_filtrado["FECHA_DT"].max() if "FECHA_DT" in df_filtrado.columns else pd.NaT

combo_critico, ranking_combo = obtener_combo_critico(df_filtrado)

k1, k2, k3, k4 = st.columns(4)
k1.metric("📊 Total mantenciones", total_mant)
k2.metric("🔥 Mantención más frecuente", mant_top)
k3.metric("📅 Fecha inicio", formatear_fecha(fecha_inicio))
k4.metric("📅 Fecha fin", formatear_fecha(fecha_fin))

# =========================
# RESPUESTAS AUTOMÁTICAS
# =========================
st.subheader("🎯 Respuesta automática: criticidad")

if combo_critico is not None:
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("🏭 Equipo crítico", str(combo_critico["EQUIPO"]))
    r2.metric("📦 Formato crítico", str(combo_critico["FORMATO_STD"]))
    r3.metric("⚙️ Cabezal crítico", int(combo_critico["N° CABEZAL"]))
    r4.metric("🌺 Tulipa crítica", int(combo_critico["N° TULIPA"]))

    st.success(f"**Combinación más crítica:** {combo_critico['EQUIPO']} | {combo_critico['FORMATO_STD']} | Cabezal {int(combo_critico['N° CABEZAL'])} | Tulipa {int(combo_critico['N° TULIPA'])} (x{int(combo_critico['Frecuencia'])})")

# =========================
# TOP FRECUENCIAS
# =========================
st.subheader("🏆 TOP Equipo/Formato/Cabezal/Tulipa")
t1, t2, t3, t4 = st.columns(4)
with t1: st.dataframe(top_tabla(df_filtrado, "EQUIPO"), use_container_width=True)
with t2: st.dataframe(top_tabla(df_filtrado, "FORMATO_STD", "FORMATO"), use_container_width=True)
with t3: st.dataframe(top_tabla(df_filtrado, "N° CABEZAL"), use_container_width=True)
with t4: st.dataframe(top_tabla(df_filtrado, "N° TULIPA"), use_container_width=True)

# =========================
# GRÁFICOS ORIGINALES
# =========================
col1, col2 = st.columns(2)
with col1:
    if "FECHA_DT" in df_filtrado.columns and not df_filtrado["FECHA_DT"].dropna().empty:
        serie = df_filtrado.groupby(df_filtrado["FECHA_DT"].dt.date).size().reset_index(name="Cantidad")
        fig = px.line(serie, x="FECHA_DT", y="Cantidad", markers=True, title="Mantenciones por día")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    mant = df_filtrado["MANTENCIÓN"].value_counts().reset_index()
    mant.columns = ["MANTENCIÓN", "Cantidad"]
    fig = px.bar(mant, x="MANTENCIÓN", y="Cantidad", title="Frecuencia por tipo")
    st.plotly_chart(fig, use_container_width=True)

# Más gráficos...
col3, col4 = st.columns(2)
with col3:
    op = df_filtrado["OPERADOR"].value_counts().reset_index()
    op.columns = ["OPERADOR", "Cantidad"]
    fig = px.bar(op, x="OPERADOR", y="Cantidad")
    st.plotly_chart(fig, use_container_width=True)

with col4:
    eq = df_filtrado["EQUIPO"].value_counts().reset_index()
    eq.columns = ["EQUIPO", "Cantidad"]
    fig = px.pie(eq, names="EQUIPO", values="Cantidad")
    st.plotly_chart(fig, use_container_width=True)

# =========================
# 4 DIAGRAMAS DE CALOR
# =========================
st.markdown("---")
st.subheader("🔥 ESQUEMAS: 4 Diagramas por Equipo/Formato")

equipos_base = ["ENCAJONADORA", "DESENCAJONADORA"]
for equipo in equipos_base:
    st.markdown(f"### {equipo}")
    c1, c2 = st.columns(2)

    with c1:
        fig_2000, matriz_2000 = crear_heatmap_formato(df_filtrado, equipo, "2.000 CC")
        if fig_2000:
            st.plotly_chart(fig_2000, use_container_width=True)
            st.dataframe(matriz_2000, use_container_width=True)
        else:
            st.info("Sin datos 2.000 CC")

    with c2:
        fig_2500, matriz_2500 = crear_heatmap_formato(df_filtrado, equipo, "2.500 CC")
        if fig_2500:
            st.plotly_chart(fig_2500, use_container_width=True)
            st.dataframe(matriz_2500, use_container_width=True)
        else:
            st.info("Sin datos 2.500 CC")

# =========================
# CRUCE Y DETALLE
# =========================
st.subheader("📊 Cruce Equipo vs Mantención")
if {"EQUIPO", "MANTENCIÓN"}.issubset(df_filtrado.columns):
    tabla_cruce = pd.crosstab(df_filtrado["EQUIPO"], df_filtrado["MANTENCIÓN"])
    st.dataframe(tabla_cruce, use_container_width=True)

st.subheader("📋 Detalle Registros")
columnas_mostrar = [c for c in ["FECHA", "TURNO", "OPERADOR", "EQUIPO", "FORMATO", "SABOR", "N° CABEZAL", "N° TULIPA", "MANTENCIÓN", "OBSERVACIÓN"] if c in df_filtrado.columns]
st.dataframe(df_filtrado[columnas_mostrar], use_container_width=True)

# =========================
# DESCARGA
# =========================
csv = df_filtrado.to_csv(index=False).encode("utf-8-sig")
st.download_button("💾 Descargar CSV", csv, "mantenciones.csv", "text/csv")