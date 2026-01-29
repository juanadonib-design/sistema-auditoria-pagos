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
    importe TEXT
)
""")
conn.commit()

def guardar_registro(datos):
    cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe)
        VALUES (?, ?, ?, ?)
    """, (
        datos["Institucion"],
        datos["Estructura"],
        datos["Libramiento"],
        datos["Importe"]
    ))
    conn.commit()

# ================= EXTRACCIÓN =================
def extraer_datos(texto):
    institucion = re.search(r'INSTITUTO|MINISTERIO|DIRECCIÓN|AYUNTAMIENTO|UNIVERSIDAD.*', texto, re.IGNORECASE)
    estructura = re.search(r'\b\d{12}\b', texto)
    libramiento = re.search(r'\b\d{1,5}\b', texto)
    importe = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)

    return {
        "Institucion": institucion.group(0) if institucion else "No encontrado",
        "Estructura": estructura.group(0) if estructura else "No encontrado",
        "Libramiento": libramiento.group(0) if libramiento else "No encontrado",
        "Importe": importe.group(0) if importe else "No encontrado"
    }

# ================= ENTRADA AUTOMÁTICA POR PEGADO =================
texto_pegado = st.text_area("📥 Pegue el texto del documento aquí (El análisis es automático)")

# Si hay texto, se analiza de una vez sin esperar al botón
if texto_pegado:
    registro = extraer_datos(texto_pegado)
    
    st.write("### 🔍 Datos Detectados")
    st.table(pd.DataFrame([registro]))
    
    # El botón ahora solo sirve para CONFIRMAR el guardado en la DB
    if st.button("💾 Confirmar y Guardar en Historial"):
        guardar_registro(registro)
        st.success("Registro guardado en el historial")

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial de Registros")
df_historial = pd.read_sql_query("SELECT * FROM registros", conn)
st.dataframe(df_historial)

# ================= FUNCIÓN PARA CREAR FORMULARIOS VERTICALES =================
def crear_formulario_auditoria(titulo, columnas, clave_storage):
    st.markdown("---")
    st.header(f"📋 {titulo}")
    
    df_init = pd.DataFrame([{col: "√" for col in columnas}])
    
    # Mantenemos el ancho de 65px para forzar el formato vertical tipo sello
    config = {
        col: st.column_config.SelectboxColumn(
            label=col, 
            options=["√", "N/A"],
            width=65, 
            required=True
        ) for col in columnas
    }

    editor = st.data_editor(
        df_init,
        column_config=config,
        use_container_width=False,
        hide_index=True,
        key=clave_storage
    )
    
    fila = editor.iloc[0]
    faltantes = [col for col in columnas if fila[col] == "N/A"]
    
    if faltantes:
        st.warning(f"⚠️ Faltan en {titulo}: {', '.join(faltantes)}")
    else:
        st.success(f"✅ Expediente de {titulo} completo")

# ================= RENDERIZADO DE LOS 3 FORMULARIOS =================

# 1. BIENES Y SERVICIOS
cols_bienes = ["CC", "CP", "OFI", "FACT", "FIRMA DIGITAL", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "TITULO", "DETE", "JURI INMO", "TASACIÓN", "APROB. PRESI", "VIAJE PRESI"]
crear_formulario_auditoria("Formulario Bienes y Servicios", cols_bienes, "f_bienes")

# 2. TRANSFERENCIAS
cols_transf = ["OFI", "FIRMA DIGITAL", "PRES", "OFIC", "BENE", "NÓMINA", "CARTA RUTA", "RNC", "MERCADO VA", "DECRETO", "CONGRESO", "DIR. FIDE", "CONTR. FIDU", "DEUDA EXT", "ANTICIPO"]
crear_formulario_auditoria("Formulario de Transferencias", cols_transf, "f_transf")

# 3. OBRAS
cols_obras = ["CC", "CP", "OFI", "FIRMA DIGITAL", "FACT", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "EVATEC", "CU", "SUP", "Cierre de Obra", "20%", "AVA", "FIEL"]
crear_formulario_auditoria("Formulario de Obras", cols_obras, "f_obras")

st.markdown("---")
st.info("Complete las verificaciones arriba y presione Ctrl+P para imprimir su reporte si es necesario.")
