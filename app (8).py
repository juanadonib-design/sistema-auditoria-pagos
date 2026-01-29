import streamlit as st
import pandas as pd
import re
import sqlite3

st.set_page_config(page_title="Sistema Auditoría de Pagos", layout="wide")
st.title("🧾 Sistema de Apoyo a la Auditoría de Pagos")

# ================= BASE DE DATOS (CON REPARACIÓN AUTOMÁTICA) =================
conn = sqlite3.connect("auditoria.db", check_same_thread=False)
cursor = conn.cursor()

# Creamos la tabla base si no existe
cursor.execute("""
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    institucion TEXT,
    estructura_programatica TEXT,
    numero_libramiento TEXT,
    importe TEXT
)
""")

# Verificación de columna 'clasificacion' para evitar OperationalError
cursor.execute("PRAGMA table_info(registros)")
columnas = [info[1] for info in cursor.fetchall()]
if "clasificacion" not in columnas:
    cursor.execute("ALTER TABLE registros ADD COLUMN clasificacion TEXT DEFAULT 'General'")
    conn.commit()

# ================= EXTRACCIÓN Y CLASIFICACIÓN OPTIMIZADA =================
def extraer_datos(texto):
    # INSTITUCIÓN: Busca palabras clave y captura el resto de la línea
    institucion_match = re.search(r'(INSTITUTO|MINISTERIO|DIRECCIÓN|AYUNTAMIENTO|UNIVERSIDAD|CONSEJO|TESORERÍA|CONTRALORÍA)\b.*', texto, re.IGNORECASE)
    
    # ESTRUCTURA: Busca exactamente 12 dígitos (Estándar SIGEF)
    estructura_match = re.search(r'\b\d{12}\b', texto)
    
    # LIBRAMIENTO: Intenta buscar etiquetas comunes primero para no fallar
    libramiento_match = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    
    # Si no encuentra etiqueta, busca un número corto aislado (1-6 dígitos)
    if not libramiento_match:
        libramiento_match = re.search(r'\b\d{1,6}\b', texto)

    # IMPORTE: Busca el formato de moneda dominicano
    importe_match = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    
    # Condición para SERVICIOS BASICOS
    clasificacion = "General"
    if "SERVICIOS BASICOS" in texto.upper():
        clasificacion = "SERVICIOS BASICOS"

    return {
        "institucion": institucion_match.group(0).strip() if institucion_match else "No encontrado",
        "estructura_programatica": estructura_match.group(0) if estructura_match else "No encontrado",
        "numero_libramiento": libramiento_match.group(1) if (libramiento_match and len(libramiento_match.groups()) > 0) else (libramiento_match.group(0) if libramiento_match else "No encontrado"),
        "importe": importe_match.group(0) if importe_match else "No encontrado",
        "clasificacion": clasificacion
    }

# ================= ENTRADA Y GUARDADO AUTOMÁTICO =================
texto_pegado = st.text_area("📥 Pegue el texto aquí (Análisis y guardado instantáneo)", key="input_auditoria")

if texto_pegado:
    nuevo_registro = extraer_datos(texto_pegado)
    
    cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion)
        VALUES (?, ?, ?, ?, ?)
    """, (nuevo_registro["institucion"], nuevo_registro["estructura_programatica"], 
          nuevo_registro["numero_libramiento"], nuevo_registro["importe"], nuevo_registro["clasificacion"]))
    conn.commit()
    
    if nuevo_registro["clasificacion"] == "SERVICIOS BASICOS":
        st.info("💡 Se ha detectado un expediente de **SERVICIOS BASICOS**. El Formulario de Bienes y Servicios ha sido resaltado.")
    
    st.toast(f"✅ Registro {nuevo_registro['clasificacion']} guardado", icon="🚀")

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

    # Si el auditor modifica algo en el historial, se guarda solo
    if not historial_editado.equals(df_historial):
        historial_editado.to_sql("registros", conn, if_exists="replace", index=False)
        st.toast("💾 Cambios guardados automáticamente", icon="☁️")
else:
    st.info("El historial aparecerá aquí en cuanto pegue información.")

# ================= FUNCIÓN PARA FORMULARIOS =================
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

    st.data_editor(
        df_init,
        column_config=config,
        use_container_width=False,
        hide_index=True,
        key=clave_storage
    )

# ================= RENDERIZADO DE FORMULARIOS =================
es_servicios_basicos = False
if not df_historial.empty:
    es_servicios_basicos = df_historial.iloc[0]["clasificacion"] == "SERVICIOS BASICOS"

# 1. BIENES Y SERVICIOS
cols_bienes = ["CC", "CP", "OFI", "FACT", "FIRMA DIGITAL", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "TITULO", "DETE", "JURI INMO", "TASACIÓN", "APROB. PRESI", "VIAJE PRESI"]
crear_formulario_auditoria("Formulario Bienes y Servicios", cols_bienes, "f_bienes", resaltar=es_servicios_basicos)

# 2. TRANSFERENCIAS
cols_transf = ["OFI", "FIRMA DIGITAL", "PRES", "OFIC", "BENE", "NÓMINA", "CARTA RUTA", "RNC", "MERCADO VA", "DECRETO", "CONGRESO", "DIR. FIDE", "CONTR. FIDU", "DEUDA EXT", "ANTICIPO"]
crear_formulario_auditoria("Formulario de Transferencias", cols_transf, "f_transf")

# 3. OBRAS
cols_obras = ["CC", "CP", "OFI", "FIRMA DIGITAL", "FACT", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "EVATEC", "CU", "SUP", "Cierre de Obra", "20%", "AVA", "FIEL"]
crear_formulario_auditoria("Formulario de Obras", cols_obras, "f_obras")
