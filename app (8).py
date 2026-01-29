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

# ================= EXTRACCIÓN Y CLASIFICACIÓN MEJORADA =================
def extraer_datos(texto):
    # Limpiamos el texto de espacios extraños al inicio
    texto_clean = texto.strip()
    lineas = texto_clean.split('\n')

    # 1. INSTITUCIÓN: Intento con palabras clave primero
    institucion_match = re.search(r'(INSTITUTO|MINISTERIO|DIRECCIÓN|AYUNTAMIENTO|UNIVERSIDAD|CONSEJO|TESORERÍA|CONTRALORÍA|ESTADO|PRESIDENCIA|ALCALDÍA)\b.*', texto, re.IGNORECASE)
    
    institucion_final = "No encontrado"
    if institucion_match:
        institucion_final = institucion_match.group(0).strip()
    elif len(lineas) > 0:
        # Si no hay palabra clave, tomamos la primera línea con texto (suele ser el encabezado)
        for linea in lineas:
            if len(linea.strip()) > 5: # Evitamos líneas vacías o muy cortas
                institucion_final = linea.strip()
                break
    
    # 2. ESTRUCTURA: 12 dígitos
    estructura_match = re.search(r'\b\d{12}\b', texto)
    
    # 3. LIBRAMIENTO: Tu versión que ya funciona
    libramiento_match = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    if not libramiento_match:
        libramiento_match = re.search(r'\b\d{1,6}\b', texto)

    # 4. IMPORTE
    importe_match = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    
    # CLASIFICACIÓN SERVICIOS BASICOS
    clasificacion = "General"
    if "SERVICIOS BASICOS" in texto.upper():
        clasificacion = "SERVICIOS BASICOS"

    return {
        "institucion": institucion_final,
        "estructura_programatica": estructura_match.group(0) if estructura_match else "No encontrado",
        "numero_libramiento": libramiento_match.group(1) if (libramiento_match and len(libramiento_match.groups()) > 0) else (libramiento_match.group(0) if libramiento_match else "No encontrado"),
        "importe": importe_match.group(0) if importe_match else "No encontrado",
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

# ================= HISTORIAL EDITABLE (AUTOGUARDADO) =================
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
    
    config = {
        col: st.column_config.SelectboxColumn(
            label=col, options=["√", "N/A"], width=65, required=True
        ) for col in columnas
    }

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
