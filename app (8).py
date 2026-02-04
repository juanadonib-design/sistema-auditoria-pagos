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
# 🔐 TABLA DE USUARIOS
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    usuario TEXT UNIQUE,
    password TEXT
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
    
# 🔗 Relacionar registros con usuario
cursor.execute("PRAGMA table_info(registros)")
cols = [c[1] for c in cursor.fetchall()]

if "usuario_id" not in cols:
    cursor.execute("ALTER TABLE registros ADD COLUMN usuario_id INTEGER")
    conn.commit()
    
if "estado" not in columnas_existentes:
    cursor.execute("ALTER TABLE registros ADD COLUMN estado TEXT DEFAULT 'En proceso'")
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
# ================= LOGIN =================
if "usuario_id" not in st.session_state:
    st.subheader("🔐 Iniciar Sesión")

    user = st.text_input("Usuario")
    pwd = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        u = cursor.execute(
            "SELECT id FROM usuarios WHERE usuario=? AND password=?",
            (user, pwd)
        ).fetchone()

        if u:
            st.session_state.usuario_id = u[0]
            st.success("Bienvenido")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

    st.stop()
    
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
INSERT INTO registros (
    institucion, estructura_programatica, numero_libramiento,
    importe, clasificacion, rnc, cuenta_objetal, usuario_id
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    nuevo_registro["institucion"],
    nuevo_registro["estructura_programatica"],
    nuevo_registro["numero_libramiento"],
    nuevo_registro["importe"],
    nuevo_registro["clasificacion"],
    nuevo_registro["rnc"],
    cuenta_objetal_manual,
    st.session_state.usuario_id
))
    conn.commit()

    st.success("Registro guardado")
    st.rerun()

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial")
def colorear_estado(val):
    if val == "En proceso":
        return "background-color:#ffe5e5; color:red; font-weight:bold"
    elif val == "Completado":
        return "background-color:#e6ffe6; color:green; font-weight:bold"
    return ""
    
st.dataframe(
    df_historial.style.applymap(colorear_estado, subset=["estado"]),
    use_container_width=True
)

df_historial = pd.read_sql_query("""
SELECT 
    id,
    institucion,
    numero_libramiento,
    estructura_programatica,
    importe,
    cuenta_objetal,
    clasificacion,
    estado
FROM registros
WHERE usuario_id = ?
ORDER BY id DESC
""", conn, params=(st.session_state.usuario_id,))

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

        # ✅ MARCAR EXPEDIENTE COMO COMPLETADO
        cursor.execute(
            "UPDATE registros SET estado='Completado' WHERE id=?",
            (registro_id,)
        )
        conn.commit()

        st.success("Formulario guardado correctamente")


# MOSTRAR FORMULARIO SOLO SI ES SB
if registro_sel:
    clasif = df_historial.loc[df_historial.id==registro_sel,"clasificacion"].values[0]
    if clasif == "SERVICIOS BASICOS":
        crear_formulario_bienes_servicios(registro_sel)

# =====================================================
# 📤 EXPORTACIÓN GENERAL DEL SISTEMA (DEBAJO DE FORMULARIOS)
# =====================================================
import io

st.markdown("---")
st.markdown("## 📤 Exportación General del Sistema")

if st.button("📥 Exportar TODOS los expedientes a Excel"):

    df_export = pd.read_sql_query("""
        SELECT
            r.institucion,
            r.estructura_programatica,
            r.numero_libramiento,
            r.importe,
            r.cuenta_objetal,
            r.clasificacion,

            f.CC, f.CP, f.OFI, f.FACT, f.FIRMA_DIGITAL, f.Recep,
            f.RPE, f.DGII, f.TSS, f.OC, f.CONT, f.TITULO,
            f.DETE, f.JURI_INMO, f.TASACION, f.APROB_PRESI, f.VIAJE_PRESI

        FROM registros r
        LEFT JOIN formulario_bienes_servicios f
        ON r.id = f.registro_id

        ORDER BY r.id DESC
    """, conn)

    buffer = io.BytesIO()
    df_export.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "⬇️ Descargar Excel General",
        buffer,
        file_name="Auditoria_Completa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )




