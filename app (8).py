import streamlit as st
import pandas as pd
import re
import sqlite3
import time

st.set_page_config(page_title="Sistema Auditoría de Pagos", layout="wide")
st.title("🧾 Sistema de Apoyo a la Auditoría de Pagos")

st.markdown("""
<style>
.badge-en-uso {
    display: inline-block;
    background-color: #28a745;
    color: white;
    padding: 4px 15px;
    border-radius: 50px;
    font-size: 14px;
    font-weight: bold;
    margin-left: 15px;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)

if "texto_input" not in st.session_state:
    st.session_state.texto_input = ""

# ================= BASE DE DATOS =================
conn = sqlite3.connect("auditoria.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    institucion TEXT,
    estructura_programatica TEXT,
    numero_libramiento TEXT,
    importe TEXT,
    clasificacion TEXT
)
""")

# 🔹 TABLA FORMULARIO BIENES Y SERVICIOS RELACIONADA
cursor.execute("""
CREATE TABLE IF NOT EXISTS formularios_bs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registro_id INTEGER UNIQUE,
    CC TEXT, CP TEXT, OFI TEXT, FACT TEXT, FIRMA_DIGITAL TEXT,
    Recep TEXT, RPE TEXT, DGII TEXT, TSS TEXT, OC TEXT, CONT TEXT,
    TITULO TEXT, DETE TEXT, JURI_INMO TEXT, TASACION TEXT,
    APROB_PRESI TEXT, VIAJE_PRESI TEXT,
    FOREIGN KEY(registro_id) REFERENCES registros(id)
)
""")
conn.commit()

# ================= EXTRACCIÓN =================
def extraer_datos(texto):
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    institucion_final = "No encontrado"
    estructura_final = "No encontrado"
    libramiento_final = "No encontrado"
    importe_final = "No encontrado"
    clasificacion = "General"

    for i, linea in enumerate(lineas):
        if re.search(r'\bINSTITUCI[ÓO]N\b', linea, re.IGNORECASE):
            if i + 1 < len(lineas):
                institucion_final = lineas[i+1]
        elif re.search(r'\b(MINISTERIO|INABIE|DIRECCION|ALCALDIA|AYUNTAMIENTO)\b', linea, re.IGNORECASE):
            if institucion_final == "No encontrado":
                institucion_final = linea

    est_match = re.search(r'\b\d{12}\b', texto)
    if est_match:
        estructura_final = est_match.group(0)

    lib_match = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    if lib_match:
        libramiento_final = lib_match.group(1)

    imp_match = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    if imp_match:
        importe_final = imp_match.group(0)

    if "SERVICIOS BASICOS" in texto.upper():
        clasificacion = "SERVICIOS BASICOS"

    return {
        "institucion": institucion_final,
        "estructura_programatica": estructura_final,
        "numero_libramiento": libramiento_final,
        "importe": importe_final,
        "clasificacion": clasificacion
    }

# ================= ENTRADA =================
texto_pegado = st.text_area("📥 Pegue el texto aquí", value=st.session_state.texto_input)

if st.button("📤 Enviar al Historial"):
    if texto_pegado.strip():
        nuevo_registro = extraer_datos(texto_pegado)

        cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion) 
        VALUES (?, ?, ?, ?, ?)
        """, tuple(nuevo_registro.values()))
        conn.commit()

        st.session_state.texto_input = ""
        st.success("Registro guardado")
        st.rerun()

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial")
df_historial = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", conn)

if not df_historial.empty:
    st.dataframe(df_historial, use_container_width=True)

# ================= SELECCIONAR EXPEDIENTE =================
registro_sel = None
if not df_historial.empty:
    registro_sel = st.selectbox(
        "📌 Seleccione expediente",
        df_historial["id"],
        format_func=lambda x: f"#{x} — {df_historial[df_historial.id==x]['institucion'].values[0]}"
    )

# ================= FORMULARIO BIENES Y SERVICIOS =================
columnas_bs = ["CC","CP","OFI","FACT","FIRMA DIGITAL","Recep","RPE","DGII","TSS","OC",
               "CONT","TITULO","DETE","JURI INMO","TASACIÓN","APROB. PRESI","VIAJE PRESI"]

if registro_sel:
    datos_registro = df_historial[df_historial["id"] == registro_sel].iloc[0]

    if datos_registro["clasificacion"] == "SERVICIOS BASICOS":
        st.markdown('### 📋 Bienes y Servicios <span class="badge-en-uso">En uso</span>', unsafe_allow_html=True)

        df_exist = pd.read_sql_query(
            f"SELECT * FROM formularios_bs WHERE registro_id={registro_sel}", conn
        )

        if df_exist.empty:
            df_form = pd.DataFrame([{col: "√" for col in columnas_bs}])
        else:
            df_form = df_exist.rename(columns={
                "FIRMA_DIGITAL":"FIRMA DIGITAL",
                "JURI_INMO":"JURI INMO",
                "TASACION":"TASACIÓN",
                "APROB_PRESI":"APROB. PRESI",
                "VIAJE_PRESI":"VIAJE PRESI"
            })[columnas_bs]

        config = {col: st.column_config.SelectboxColumn(options=["√","N/A"], width=65) for col in columnas_bs}
        tabla_editable = st.data_editor(df_form, column_config=config, hide_index=True)

        if st.button("💾 Guardar Formulario"):
            guardar_df = tabla_editable.rename(columns={
                "FIRMA DIGITAL":"FIRMA_DIGITAL",
                "JURI INMO":"JURI_INMO",
                "TASACIÓN":"TASACION",
                "APROB. PRESI":"APROB_PRESI",
                "VIAJE PRESI":"VIAJE_PRESI"
            })
            guardar_df["registro_id"] = registro_sel

            cursor.execute("DELETE FROM formularios_bs WHERE registro_id=?", (registro_sel,))
            conn.commit()

            guardar_df.to_sql("formularios_bs", conn, if_exists="append", index=False)
            st.success("Formulario guardado correctamente")
