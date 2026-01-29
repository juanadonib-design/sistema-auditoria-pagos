import streamlit as st
import pandas as pd
import re
import sqlite3

st.set_page_config(page_title="Sistema Auditoría de Pagos", layout="wide")
st.title("🧾 Sistema de Apoyo a la Auditoría de Pagos")

# ================= BASE DE DATOS (CON REPARACIÓN AUTOMÁTICA) =================
conn = sqlite3.connect("auditoria.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    institucion TEXT,
    estructura_programatica TEXT,
    numero_libramiento TEXT,
    importe TEXT
)
""")

cursor.execute("PRAGMA table_info(registros)")
columnas = [info[1] for info in cursor.fetchall()]
if "clasificacion" not in columnas:
    cursor.execute("ALTER TABLE registros ADD COLUMN clasificacion TEXT DEFAULT 'General'")
    conn.commit()

# ================= EXTRACCIÓN MEJORADA (SALTOS DE LÍNEA) =================
def extraer_datos(texto):
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    
    institucion_final = "No encontrado"
    estructura_final = "No encontrado"
    libramiento_final = "No encontrado"
    importe_final = "No encontrado"
    clasificacion = "General"

    # 1. BÚSQUEDA DE INSTITUCIÓN (Detecta INABIE en línea siguiente)
    for i, linea in enumerate(lineas):
        # Busca palabras clave de encabezado
        if re.search(r'INSTITUCION|MINISTERIO|DIRECCION|AYUNTAMIENTO|UNIVERSIDAD|INABIE', linea, re.IGNORECASE):
            # Si la línea solo dice "Institucion" o similar, toma la siguiente
            if len(linea) < 15 and i + 1 < len(lineas):
                institucion_final = lineas[i+1]
            else:
                institucion_final = linea
            break

    # 2. BÚSQUEDA DE ESTRUCTURA (12 dígitos)
    est_match = re.search(r'\b\d{12}\b', texto)
    if est_match: estructura_final = est_match.group(0)

    # 3. BÚSQUEDA DE LIBRAMIENTO (Usa tu lógica probada)
    lib_match = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    if lib_match: 
        libramiento_final = lib_match.group(1) if lib_match.groups() else lib_match.group(0)
    else:
        # Búsqueda secundaria de número corto
        sec_lib = re.search(r'\b\d{1,6}\b', texto)
        if sec_lib: libramiento_final = sec_lib.group(0)

    # 4. BÚSQUEDA DE IMPORTE
    imp_match = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    if imp_match: importe_final = imp_match.group(0)

    # 5. CLASIFICACIÓN SERVICIOS BASICOS
    if "SERVICIOS BASICOS" in texto.upper():
        clasificacion = "SERVICIOS BASICOS"

    return {
        "institucion": institucion_final,
        "estructura_programatica": estructura_final,
        "numero_libramiento": libramiento_final,
        "importe": importe_final,
        "clasificacion": clasificacion
    }

# ================= ENTRADA Y GUARDADO AUTOMÁTICO =================
texto_pegado = st.text_area("📥 Pegue el texto aquí (Análisis instantáneo)", key="input_auditoria")

if texto_pegado:
    nuevo_registro = extraer_datos(texto_pegado)
    
    cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion)
        VALUES (?, ?, ?, ?, ?)
    """, (nuevo_registro["institucion"], nuevo_registro["estructura_programatica"], 
          nuevo_registro["numero_libramiento"], nuevo_registro["importe"], nuevo_registro["clasificacion"]))
    conn.commit()
    
    if nuevo_registro["clasificacion"] == "SERVICIOS BASICOS":
        st.info("💡 Se ha detectado un expediente de **SERVICIOS BASICOS**.")
    
    st.toast(f"✅ Registro guardado", icon="🚀")

# ================= HISTORIAL EDITABLE =================
st.markdown("---")
st.subheader("📊 Historial Editable (Autoguardado)")

df_historial = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", conn)

if not df_historial.empty:
    historial_editado = st.data_editor(
        df_historial,
        key="editor_historial",
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )

    if not historial_editado.equals(df_historial):
        historial_editado.to_sql("registros", conn, if_exists="replace", index=False)
        st.toast("💾 Cambios guardados", icon="☁️")
else:
    st.info("El historial aparecerá aquí.")

# ================= FORMULARIOS =================
def crear_formulario_auditoria(titulo, columnas, clave_storage, resaltar=False):
    if resaltar:
        st.markdown(f"### 🌟 {titulo} (Recomendado)")
    else:
        st.markdown(f"### 📋 {titulo}")
    
    df_init = pd.DataFrame([{col: "√" for col in columnas}])
    config = {col: st.column_config.SelectboxColumn(label=col, options=["√", "N/A"], width=65, required=True) for col in columnas}
    st.data_editor(df_init, column_config=config, use_container_width=False, hide_index=True, key=clave_storage)

es_servicios_basicos = False
if not df_historial.empty:
    es_servicios_basicos = df_historial.iloc[0]["clasificacion"] == "SERVICIOS BASICOS"

cols_bienes = ["CC", "CP", "OFI", "FACT", "FIRMA DIGITAL", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "TITULO", "DETE", "JURI INMO", "TASACIÓN", "APROB. PRESI", "VIAJE PRESI"]
crear_formulario_auditoria("Formulario Bienes y Servicios", cols_bienes, "f_bienes", resaltar=es_servicios_basicos)

cols_transf = ["OFI", "FIRMA DIGITAL", "PRES", "OFIC", "BENE", "NÓMINA", "CARTA RUTA", "RNC", "MERCADO VA", "DECRETO", "CONGRESO", "DIR. FIDE", "CONTR. FIDU", "DEUDA EXT", "ANTICIPO"]
crear_formulario_auditoria("Formulario de Transferencias", cols_transf, "f_transf")

cols_obras = ["CC", "CP", "OFI", "FIRMA DIGITAL", "FACT", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "EVATEC", "CU", "SUP", "Cierre de Obra", "20%", "AVA", "FIEL"]
crear_formulario_auditoria("Formulario de Obras", cols_obras, "f_obras")
