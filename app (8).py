import streamlit as st
import pandas as pd
import re
import sqlite3
import time
import unicodedata

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

# ================= BASE DE DATOS =================
conn = sqlite3.connect("auditoria.db", check_same_thread=False)
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    institucion TEXT,
    estructura_programatica TEXT,
    numero_libramiento TEXT,
    importe TEXT,
    clasificacion TEXT,
    rnc TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS formulario_bienes_servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registro_id INTEGER UNIQUE,
    CC TEXT, CP TEXT, OFI TEXT, FACT TEXT, FIRMA_DIGITAL TEXT, Recep TEXT,
    RPE TEXT, DGII TEXT, TSS TEXT, OC TEXT, CONT TEXT, TITULO TEXT,
    DETE TEXT, JURI_INMO TEXT, TASACION TEXT, APROB_PRESI TEXT, VIAJE_PRESI TEXT,
    FOREIGN KEY(registro_id) REFERENCES registros(id) ON DELETE CASCADE
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

    rnc_match = re.search(r'\b\d{9,11}\b', texto)
    rnc_final = rnc_match.group(0) if rnc_match else "No encontrado"

    for i, linea in enumerate(lineas):
        if re.search(r'\bINSTITUCI[ÓO]N\b', linea, re.IGNORECASE):
            if i + 1 < len(lineas):
                institucion_final = lineas[i+1]

    est_match = re.search(r'\b\d{12}\b', texto)
    if est_match: estructura_final = est_match.group(0)

    lib_match = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    if lib_match: libramiento_final = lib_match.group(1)

    imp_match = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    if imp_match: importe_final = imp_match.group(0)

    texto_norm = unicodedata.normalize('NFD', texto.upper()).encode('ascii','ignore').decode()
    if "SERVICIOS BASICOS" in texto_norm:
        clasificacion = "SERVICIOS BASICOS"

    return {
        "institucion": institucion_final,
        "estructura_programatica": estructura_final,
        "numero_libramiento": libramiento_final,
        "importe": importe_final,
        "clasificacion": clasificacion,
        "rnc": rnc_final
    }

# ================= ENTRADA =================
texto_pegado = st.text_area("📥 Pegue el texto aquí")

if st.button("📤 Enviar al Historial"):
    nuevo_registro = extraer_datos(texto_pegado)

    cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion, rnc) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        nuevo_registro["institucion"],
        nuevo_registro["estructura_programatica"],
        nuevo_registro["numero_libramiento"],
        nuevo_registro["importe"],
        nuevo_registro["clasificacion"],
        nuevo_registro["rnc"]
    ))
    conn.commit()
    st.rerun()

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial")
df_historial = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", conn)

registro_sel = None
if not df_historial.empty:
    registro_sel = st.selectbox(
        "📌 Seleccione expediente",
        df_historial["id"],
        format_func=lambda x: f"#{x} — {df_historial.loc[df_historial.id==x,'institucion'].values[0]}"
    )

    if st.button("🗑️ Borrar expediente seleccionado"):
        cursor.execute("DELETE FROM registros WHERE id = ?", (registro_sel,))
        conn.commit()
        st.rerun()

# ================= FORMULARIO =================
def crear_formulario_bienes_servicios(registro_id):

    rnc = pd.read_sql_query(f"SELECT rnc FROM registros WHERE id={registro_id}", conn).iloc[0]["rnc"]

    condicion = None
    if str(rnc).startswith("1"):
        condicion = 1
    elif str(rnc).startswith("4"):
        condicion = 2

    columnas = ["CC","CP","OFI","FACT","FIRMA_DIGITAL","Recep","RPE","DGII","TSS","OC",
                "CONT","TITULO","DETE","JURI_INMO","TASACION","APROB_PRESI","VIAJE_PRESI"]

    st.markdown('### 📋 Bienes y Servicios <span class="badge-en-uso">En uso</span>', unsafe_allow_html=True)

    df_guardado = pd.read_sql_query(f"SELECT * FROM formulario_bienes_servicios WHERE registro_id={registro_id}", conn)

    if df_guardado.empty:
        valores = {col: "N/A" for col in columnas}

        if condicion == 1:
            valores.update({"OFI":"√","FACT":"√","RPE":"√","DGII":"√","TSS":"√"})

        elif condicion == 2:
            valores.update({"OFI":"√","FACT":"√"})

        df = pd.DataFrame([valores])
    else:
        df = df_guardado[columnas]

    config = {col: st.column_config.SelectboxColumn(options=["√","N/A"], width=65) for col in columnas}
    df_editado = st.data_editor(df, column_config=config, hide_index=True)

    colA, colB = st.columns(2)

    if condicion in [1,2]:
        if colA.button("✔ Marcar CC y CP"):
            df_editado.at[0,"CC"] = "√"
            df_editado.at[0,"CP"] = "√"

    if condicion == 2:
        if colB.button("✔ Marcar DGII, TSS y RPE"):
            df_editado.at[0,"DGII"] = "√"
            df_editado.at[0,"TSS"] = "√"
            df_editado.at[0,"RPE"] = "√"

    if st.button("💾 Guardar Formulario"):
        datos = df_editado.iloc[0].to_dict()
        cursor.execute("""
            INSERT INTO formulario_bienes_servicios
            (registro_id, CC, CP, OFI, FACT, FIRMA_DIGITAL, Recep, RPE, DGII, TSS, OC, CONT, TITULO, DETE, JURI_INMO, TASACION, APROB_PRESI, VIAJE_PRESI)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(registro_id) DO UPDATE SET
            CC=excluded.CC, CP=excluded.CP, OFI=excluded.OFI, FACT=excluded.FACT,
            FIRMA_DIGITAL=excluded.FIRMA_DIGITAL, Recep=excluded.Recep, RPE=excluded.RPE,
            DGII=excluded.DGII, TSS=excluded.TSS, OC=excluded.OC, CONT=excluded.CONT,
            TITULO=excluded.TITULO, DETE=excluded.DETE, JURI_INMO=excluded.JURI_INMO,
            TASACION=excluded.TASACION, APROB_PRESI=excluded.APROB_PRESI, VIAJE_PRESI=excluded.VIAJE_PRESI
        """, (registro_id, *datos.values()))
        conn.commit()
        st.success("Formulario guardado")

if registro_sel:
    clasif = df_historial.loc[df_historial.id==registro_sel,"clasificacion"].values[0]
    if clasif == "SERVICIOS BASICOS":
        crear_formulario_bienes_servicios(registro_sel)
