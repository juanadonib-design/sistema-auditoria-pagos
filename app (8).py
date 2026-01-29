import streamlit as st
import pandas as pd
import re
import sqlite3
import time

# Configuración de página
st.set_page_config(page_title="Sistema Auditoría de Pagos", layout="wide")
st.title("🧾 Sistema de Apoyo a la Auditoría de Pagos")

# CSS para el indicador "En uso" circular verde
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
        box-shadow: 0px 2px 4px rgba(0,0,0,0.2);
    }
    </style>
    """, unsafe_allow_html=True)

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

# ================= EXTRACCIÓN (LÓGICA VERTICAL SOLICITADA) =================
def extraer_datos(texto):
    # Dividimos por líneas y limpiamos espacios
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    
    institucion_final = "No encontrado"
    estructura_final = "No encontrado"
    libramiento_final = "No encontrado"
    importe_final = "No encontrado"
    clasificacion = "General"

    for i, linea in enumerate(lineas):
        # 🔹 LÓGICA VERTICAL: Detectar "Institución" y tomar la línea de ABAJO
        if re.search(r'\bINSTITUCI[ÓO]N\b', linea, re.IGNORECASE):
            if i + 1 < len(lineas):
                institucion_final = lineas[i+1]
        
        # 🔹 Respaldo por nombre directo (ej. INABIE)
        elif re.search(r'\b(MINISTERIO|INABIE|DIRECCION|ALCALDIA|AYUNTAMIENTO)\b', linea, re.IGNORECASE):
            if institucion_final == "No encontrado":
                institucion_final = linea

    # ESTRUCTURA (12 dígitos)
    est_match = re.search(r'\b\d{12}\b', texto)
    if est_match: estructura_final = est_match.group(0)

    # LIBRAMIENTO
    lib_match = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    if lib_match: 
        libramiento_final = lib_match.group(1)
    else:
        sec_lib = re.search(r'\b\d{1,6}\b', texto)
        if sec_lib: libramiento_final = sec_lib.group(0)

    # IMPORTE
    imp_match = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    if imp_match: importe_final = imp_match.group(0)

    # CLASIFICACIÓN SERVICIOS BASICOS
    if "SERVICIOS BASICOS" in texto.upper():
        clasificacion = "SERVICIOS BASICOS"

    return {
        "institucion": institucion_final,
        "estructura_programatica": estructura_final,
        "numero_libramiento": libramiento_final,
        "importe": importe_final,
        "clasificacion": clasificacion
    }

# ================= ENTRADA Y PROCESAMIENTO =================
texto_pegado = st.text_area("📥 Pegue el texto aquí", key="input_auditoria")

if texto_pegado:
    nuevo_registro = extraer_datos(texto_pegado)
    cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion) 
        VALUES (?, ?, ?, ?, ?)
    """, (nuevo_registro["institucion"], nuevo_registro["estructura_programatica"], 
          nuevo_registro["numero_libramiento"], nuevo_registro["importe"], nuevo_registro["clasificacion"]))
    conn.commit()
    
    # ALERTA DE 3 SEGUNDOS
    if nuevo_registro["clasificacion"] == "SERVICIOS BASICOS":
        alerta_cont = st.empty()
        alerta_cont.success("🚀 CLASIFICACIÓN DETECTADA: BIENES Y SERVICIOS")
        time.sleep(3)
        alerta_cont.empty() 
    else:
        st.toast("✅ Registro procesado")

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial (Autoguardado)")
df_historial = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", conn)

if not df_historial.empty:
    historial_editado = st.data_editor(df_historial, key="editor_historial", hide_index=True, use_container_width=True, num_rows="dynamic")
    if not historial_editado.equals(df_historial):
        historial_editado.to_sql("registros", conn, if_exists="replace", index=False)
        st.toast("💾 Cambios guardados")

# ================= FORMULARIOS =================
def crear_formulario(titulo, columnas, clave, en_uso=False):
    # Título con el círculo verde "En uso" a la derecha
    if en_uso:
        st.markdown(f'### 📋 {titulo} <span class="badge-en-uso">En uso</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'### 📋 {titulo}', unsafe_allow_html=True)
    
    df = pd.DataFrame([{col: "√" for col in columnas}])
    config = {col: st.column_config.SelectboxColumn(options=["√", "N/A"], width=65) for col in columnas}
    st.data_editor(df, column_config=config, use_container_width=False, hide_index=True, key=clave)

# Determinar si el último es SB
es_sb = False
if not df_historial.empty:
    es_sb = df_historial.iloc[0]["clasificacion"] == "SERVICIOS BASICOS"

st.markdown("---")

# 1. BIENES Y SERVICIOS (Con indicador dinámico)
crear_formulario("Bienes y Servicios", ["CC", "CP", "OFI", "FACT", "FIRMA DIGITAL", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "TITULO", "DETE", "JURI INMO", "TASACIÓN", "APROB. PRESI", "VIAJE PRESI"], "f_b", en_uso=es_sb)

# 2. TRANSFERENCIAS
crear_formulario("Transferencias", ["OFI", "FIRMA DIGITAL", "PRES", "OFIC", "BENE", "NÓMINA", "CARTA RUTA", "RNC", "MERCADO VA", "DECRETO", "CONGRESO", "DIR. FIDE", "CONTR. FIDU", "DEUDA EXT", "ANTICIPO"], "f_t")

# 3. OBRAS
crear_formulario("Obras", ["CC", "CP", "OFI", "FIRMA DIGITAL", "FACT", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "EVATEC", "CU", "SUP", "Cierre de Obra", "20%", "AVA", "FIEL"], "f_o")
