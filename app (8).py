import streamlit as st
import pandas as pd
import re
import sqlite3
import time
import unicodedata
from io import BytesIO


st.set_page_config(page_title="Sistema Auditoría de Pagos", layout="wide")
st.title("🧾 Sistema de Apoyo a la Auditoría de Pagos")

# 🔵 CSS
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

# 🔧 CREAR TABLA
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

# 🔧 SI LA TABLA ES VIEJA Y NO TIENE RNC → LA AGREGA
cursor.execute("PRAGMA table_info(registros)")
columnas_existentes = [col[1] for col in cursor.fetchall()]
if "rnc" not in columnas_existentes:
    cursor.execute("ALTER TABLE registros ADD COLUMN rnc TEXT")
    conn.commit()
    
# 🔧 Si la BD es vieja y no tiene cuenta_objetal → la agrega
cursor.execute("PRAGMA table_info(registros)")
columnas_existentes = [col[1] for col in cursor.fetchall()]

if "cuenta_objetal" not in columnas_existentes:
    cursor.execute("ALTER TABLE registros ADD COLUMN cuenta_objetal TEXT")
    conn.commit()

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
    rnc_final = rnc_match.group(0) if rnc_match else ""

    for i, linea in enumerate(lineas):
        if re.search(r'\bINSTITUCI[ÓO]N\b', linea, re.IGNORECASE):
            if i + 1 < len(lineas):
                institucion_final = lineas[i+1]
        elif re.search(r'\b(MINISTERIO|INABIE|DIRECCION|ALCALDIA|AYUNTAMIENTO)\b', linea, re.IGNORECASE):
            if institucion_final == "No encontrado":
                institucion_final = linea

    est_match = re.search(r'\b\d{12}\b', texto)
    if est_match: estructura_final = est_match.group(0)

    lib_match = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    if lib_match: libramiento_final = lib_match.group(1)

    imp_match = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    if imp_match: importe_final = imp_match.group(0)

    texto_norm = unicodedata.normalize('NFD', texto.upper()).encode('ascii', 'ignore').decode('utf-8')
    if "SERVICIOS BASICOS" in texto_norm or "SERVICIO BASICO" in texto_norm:
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
cuenta_objetal_manual = st.text_input("🏷️ Cuenta Objetal (llenado manual por auditor)")

if st.button("📤 Enviar al Historial"):
    nuevo_registro = extraer_datos(texto_pegado)

    cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion, rnc, cuenta_objetal) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        nuevo_registro["institucion"],
        nuevo_registro["estructura_programatica"],
        nuevo_registro["numero_libramiento"],
        nuevo_registro["importe"],
        nuevo_registro["clasificacion"],
        nuevo_registro["rnc"],
        cuenta_objetal_manual
    ))
    conn.commit()

    st.success("Registro guardado")
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

    # 🗑 BORRADO PERMANENTE
    if st.button("🗑️ Borrar expediente seleccionado"):
        cursor.execute("DELETE FROM registros WHERE id = ?", (registro_sel,))
        conn.commit()
        st.warning("Expediente eliminado permanentemente")
        time.sleep(1)
        st.rerun()
        # ================= VISTA PREVIA TIPO EXCEL =================
    if registro_sel:
        datos_exp = df_historial[df_historial.id == registro_sel][[
            "institucion",
            "estructura_programatica",
            "numero_libramiento",
            "importe",
            "cuenta_objetal"
        ]]

        datos_exp.columns = [
            "🏢 Institución",
            "📊 Estructura Programática",
            "📄 Número Libramiento",
            "💰 Importe",
            "🧾 Cuenta Objetal"
        ]

        st.markdown("### 📄 Vista previa del expediente")

datos_exp = df_historial[df_historial.id == registro_sel][[
    "institucion",
    "estructura_programatica",
    "numero_libramiento",
    "importe",
    "cuenta_objetal"
]]

# Renombrar columnas visualmente
datos_exp.columns = [
    "Institución",
    "Estructura Programática",
    "Número Libramiento",
    "Importe",
    "Cuenta Objetal"
]

# 🔥 TABLA EDITABLE SOLO PARA CUENTA OBJETAL
datos_editados = st.data_editor(
    datos_exp,
    disabled=["Institución","Estructura Programática","Número Libramiento","Importe"],
    use_container_width=True,
    key=f"preview_{registro_sel}"
)
from io import BytesIO

def generar_excel_unificado(registro_id):
    buffer = BytesIO()

    # 🟦 DATOS DEL EXPEDIENTE
    df_exp = df_historial[df_historial.id == registro_id][[
        "institucion",
        "estructura_programatica",
        "numero_libramiento",
        "importe",
        "cuenta_objetal"
    ]]

    # 🟩 DATOS DEL FORMULARIO
    df_form = pd.read_sql_query(
        "SELECT * FROM formulario_bienes_servicios WHERE registro_id=?",
        conn,
        params=(registro_id,)
    )

    # 🧩 UNIFICAR EN UNA SOLA FILA
    if not df_form.empty:
        df_unificado = pd.concat(
            [df_exp.reset_index(drop=True), df_form.reset_index(drop=True)],
            axis=1
        )
    else:
        df_unificado = df_exp.copy()

    # 🏷 Nombres más claros
    df_unificado.rename(columns={
        "institucion": "Institución",
        "estructura_programatica": "Estructura Programática",
        "numero_libramiento": "Número Libramiento",
        "importe": "Importe",
        "cuenta_objetal": "Cuenta Objetal"
    }, inplace=True)
    
# ❌ Eliminar columnas técnicas si existen
df_unificado = df_unificado.drop(columns=["id", "registro_id"], errors="ignore")

    # 💾 Guardar en una sola hoja
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_unificado.to_excel(writer, index=False, sheet_name="Expediente Completo")

    buffer.seek(0)
    return buffer

excel_file = generar_excel_unificado(registro_sel)

st.download_button(
    label="📥 Exportar expediente unificado",
    data=excel_file,
    file_name=f"Expediente_{registro_sel}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ================= FORMULARIO =================
def crear_formulario_bienes_servicios(registro_id):
    st.markdown(
    '### 📋 Formulario de Bienes y Servicios <span class="badge-en-uso">En uso</span>',
    unsafe_allow_html=True
)

    columnas = ["CC","CP","OFI","FACT","FIRMA_DIGITAL","Recep","RPE","DGII","TSS",
                "OC","CONT","TITULO","DETE","JURI_INMO","TASACION",
                "APROB_PRESI","VIAJE_PRESI"]

    # 🔹 Obtener RNC
    rnc_df = pd.read_sql_query(
        "SELECT rnc FROM registros WHERE id=?",
        conn,
        params=(registro_id,)
    )
    if rnc_df.empty:
        st.error("No se encontró el RNC del expediente")
        return

    rnc = str(rnc_df.iloc[0]["rnc"])

    # =====================================================
    # 🎯 DATAFRAME EN MEMORIA
    # =====================================================
    if "form_bs" not in st.session_state or st.session_state.get("form_id") != registro_id:

        base = {col: "N/A" for col in columnas}

        if rnc.startswith("1"):
            base.update({"OFI":"√","FACT":"√","RPE":"√","DGII":"√","TSS":"√"})
        elif rnc.startswith("4"):
            base.update({"OFI":"√","FACT":"√"})

        st.session_state.form_bs = pd.DataFrame([base])
        st.session_state.form_id = registro_id

    # =====================================================
    # 🔘 BOTONES AUTOMÁTICOS
    # =====================================================
    if rnc.startswith("1") or rnc.startswith("4"):
        if st.button("✔ Marcar CC y CP"):
            st.session_state.form_bs.loc[0, ["CC","CP"]] = "√"

    if rnc.startswith("4"):
        if st.button("✔ Marcar DGII, TSS y RPE"):
            st.session_state.form_bs.loc[0, ["DGII","TSS","RPE"]] = "√"

    # =====================================================
    # 🧾 EDITOR
    # =====================================================
    config = {col: st.column_config.SelectboxColumn(options=["√","N/A"], width=70) for col in columnas}

    df_editado = st.data_editor(
        st.session_state.form_bs,
        column_config=config,
        hide_index=True,
        key="editor_bs"
    )

    # =====================================================
    # 💾 GUARDAR
    # =====================================================
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
        st.success("Formulario guardado correctamente")

# MOSTRAR FORMULARIO SOLO SI ES SB
if registro_sel:
    clasif = df_historial.loc[df_historial.id==registro_sel,"clasificacion"].values[0]
    if clasif == "SERVICIOS BASICOS":
        crear_formulario_bienes_servicios(registro_sel)























