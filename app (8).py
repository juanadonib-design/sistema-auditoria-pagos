import streamlit as st
import pandas as pd
import re
import sqlite3

st.set_page_config(page_title="Sistema Auditoría de Pagos", layout="wide")
st.title("🧾 Sistema de Apoyo a la Auditoría de Pagos")

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
conn.commit()

# ================= EXTRACCIÓN LÍNEA POR LÍNEA =================
def extraer_datos(texto):
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    
    institucion_final = "No encontrado"
    estructura_final = "No encontrado"
    libramiento_final = "No encontrado"
    importe_final = "No encontrado"
    clasificacion = "General"

    for i, linea in enumerate(lineas):

        # 🔹 Detectar palabra "Institución" (con o sin tilde)
        if re.search(r'\bINSTITUCI[ÓO]N\b', linea, re.IGNORECASE):
            if i + 1 < len(lineas):
                institucion_final = lineas[i+1]

        # 🔹 Si no dice "Institución" pero es nombre conocido
        elif re.search(r'\b(MINISTERIO|INABIE|DIRECCION|ALCALDIA|AYUNTAMIENTO)\b', linea, re.IGNORECASE):
            if institucion_final == "No encontrado":
                institucion_final = linea

    # ESTRUCTURA (12 dígitos)
    est_match = re.search(r'\b\d{12}\b', texto)
    if est_match:
        estructura_final = est_match.group(0)

    # LIBRAMIENTO
    lib_match = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    if lib_match:
        libramiento_final = lib_match.group(1)
    else:
        sec_lib = re.search(r'\b\d{1,6}\b', texto)
        if sec_lib:
            libramiento_final = sec_lib.group(0)

    # IMPORTE
    imp_match = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    if imp_match:
        importe_final = imp_match.group(0)

    # CLASIFICACIÓN
    if "SERVICIOS BASICOS" in texto.upper():
        clasificacion = "SERVICIOS BASICOS"

    return {
        "institucion": institucion_final,
        "estructura_programatica": estructura_final,
        "numero_libramiento": libramiento_final,
        "importe": importe_final,
        "clasificacion": clasificacion
    }

# ================= ENTRADA Y REGISTRO =================
texto_pegado = st.text_area("📥 Pegue el texto aquí", key="input_auditoria")

if texto_pegado:
    nuevo_registro = extraer_datos(texto_pegado)
    
    cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion)
        VALUES (?, ?, ?, ?, ?)
    """, (nuevo_registro["institucion"], nuevo_registro["estructura_programatica"], 
          nuevo_registro["numero_libramiento"], nuevo_registro["importe"], nuevo_registro["clasificacion"]))
    conn.commit()
    
    if nuevo_registro["clasificacion"] == "SERVICIOS BASICOS":
        st.info("💡 Detectado: Expediente de **SERVICIOS BASICOS**.")
    st.toast("✅ Datos procesados")

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial (Autoguardado)")
df_historial = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", conn)

if not df_historial.empty:
    historial_editado = st.data_editor(df_historial, key="editor_historial", hide_index=True, use_container_width=True, num_rows="dynamic")
    if not historial_editado.equals(df_historial):
        historial_editado.to_sql("registros", conn, if_exists="replace", index=False)
        st.toast("💾 Cambios guardados")
