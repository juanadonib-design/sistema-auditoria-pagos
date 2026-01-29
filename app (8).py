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

# ================= EXTRACCIÓN Y CLASIFICACIÓN =================
def extraer_datos(texto):
    institucion = re.search(r'INSTITUTO|MINISTERIO|DIRECCIÓN|AYUNTAMIENTO|UNIVERSIDAD.*', texto, re.IGNORECASE)
    estructura = re.search(r'\b\d{12}\b', texto)
    libramiento = re.search(r'\b\d{1,5}\b', texto)
    importe = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    
    # CONDICIÓN SOLICITADA: Clasificación por palabras clave
    clasificacion = "General"
    if "SERVICIOS BASICOS" in texto:
        clasificacion = "SERVICIOS BASICOS"

    return {
        "institucion": institucion.group(0) if institucion else "No encontrado",
        "estructura_programatica": estructura.group(0) if estructura else "No encontrado",
        "numero_libramiento": libramiento.group(0) if libramiento else "No encontrado",
        "importe": importe.group(0) if importe else "No encontrado",
        "clasificacion": clasificacion
    }

# ================= ENTRADA Y GUARDADO AUTOMÁTICO =================
texto_pegado = st.text_area("📥 Pegue el texto aquí (Análisis instantáneo)", key="input_auditoria")

if texto_pegado:
    nuevo_registro = extraer_datos(texto_pegado)
    
    # Insertar en la base de datos incluyendo la nueva columna de clasificación
    cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion)
        VALUES (?, ?, ?, ?, ?)
    """, (nuevo_registro["institucion"], nuevo_registro["estructura_programatica"], 
          nuevo_registro["numero_libramiento"], nuevo_registro["importe"], nuevo_registro["clasificacion"]))
    conn.commit()
    
    # Alerta visual si detecta Servicios Básicos
    if nuevo_registro["clasificacion"] == "SERVICIOS BASICOS":
        st.info("💡 Se ha detectado un expediente de **SERVICIOS BASICOS**. Utilice el Formulario de Bienes y Servicios.")
    
    st.toast(f"✅ Registro {nuevo_registro['clasificacion']} guardado", icon="🚀")

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
        st.toast("💾 Cambios guardados automáticamente", icon="☁️")
else:
    st.info("El historial aparecerá aquí en cuanto pegue información.")

# ================= FUNCIÓN PARA FORMULARIOS =================
def crear_formulario_auditoria(titulo, columnas, clave_storage, resaltar=False):
    # Si resaltar es True (porque es Servicios Básicos), añadimos un borde o color
    if resaltar:
        st.markdown(f"### 🌟 {titulo} (Sugerido para Servicios Básicos)")
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
# Chequeamos si el último registro fue Servicios Básicos para resaltar el formulario
es_servicios_basicos = False
if not df_historial.empty:
    es_servicios_basicos = df_historial.iloc[0]["clasificacion"] == "SERVICIOS BASICOS"

# 1. BIENES Y SERVICIOS (Relacionado con Servicios Básicos)
cols_bienes = ["CC", "CP", "OFI", "FACT", "FIRMA DIGITAL", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "TITULO", "DETE", "JURI INMO", "TASACIÓN", "APROB. PRESI", "VIAJE PRESI"]
crear_formulario_auditoria("Formulario Bienes y Servicios", cols_bienes, "f_bienes", resaltar=es_servicios_basicos)

# 2. TRANSFERENCIAS
cols_transf = ["OFI", "FIRMA DIGITAL", "PRES", "OFIC", "BENE", "NÓMINA", "CARTA RUTA", "RNC", "MERCADO VA", "DECRETO", "CONGRESO", "DIR. FIDE", "CONTR. FIDU", "DEUDA EXT", "ANTICIPO"]
crear_formulario_auditoria("Formulario de Transferencias", cols_transf, "f_transf")

# 3. OBRAS
cols_obras = ["CC", "CP", "OFI", "FIRMA DIGITAL", "FACT", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "EVATEC", "CU", "SUP", "Cierre de Obra", "20%", "AVA", "FIEL"]
crear_formulario_auditoria("Formulario de Obras", cols_obras, "f_obras")
