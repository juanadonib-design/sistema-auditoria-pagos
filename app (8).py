import streamlit as st
import pandas as pd
import re
import sqlite3
import time

st.set_page_config(page_title="Sistema Auditoría de Pagos", layout="wide")
st.title("🧾 Sistema de Apoyo a la Auditoría de Pagos")

# 🔵 CSS CÍRCULO EN USO
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
cursor = conn.cursor()

# Tablas principales
cursor.execute("CREATE TABLE IF NOT EXISTS registros (id INTEGER PRIMARY KEY AUTOINCREMENT, institucion TEXT, estructura_programatica TEXT, numero_libramiento TEXT, importe TEXT, clasificacion TEXT)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS formulario_bienes_servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registro_id INTEGER UNIQUE,
    CC TEXT, CP TEXT, OFI TEXT, FACT TEXT, FIRMA_DIGITAL TEXT, Recep TEXT,
    RPE TEXT, DGII TEXT, TSS TEXT, OC TEXT, CONT TEXT, TITULO TEXT,
    DETE TEXT, JURI_INMO TEXT, TASACION TEXT, APROB_PRESI TEXT, VIAJE_PRESI TEXT,
    FOREIGN KEY(registro_id) REFERENCES registros(id)
)
""")
conn.commit()

# ================= EXTRACCIÓN =================
def extraer_datos(texto):
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    institucion_final, estructura_final, libramiento_final, importe_final, clasificacion = "No encontrado", "No encontrado", "No encontrado", "No encontrado", "General"
    for i, linea in enumerate(lineas):
        if re.search(r'\bINSTITUCI[ÓO]N\b', linea, re.IGNORECASE):
            if i + 1 < len(lineas): institucion_final = lineas[i+1]
        elif re.search(r'\b(MINISTERIO|INABIE|DIRECCION|ALCALDIA|AYUNTAMIENTO)\b', linea, re.IGNORECASE):
            if institucion_final == "No encontrado": institucion_final = linea
    est_match = re.search(r'\b\d{12}\b', texto)
    if est_match: estructura_final = est_match.group(0)
    lib_match = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    if lib_match: libramiento_final = lib_match.group(1)
    else:
        sec_lib = re.search(r'\b\d{1,6}\b', texto)
        if sec_lib: libramiento_final = sec_lib.group(0)
    imp_match = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    if imp_match: importe_final = imp_match.group(0)
    if "SERVICIOS BASICOS" in texto.upper() or "SERVICIO BASICO" in texto.upper():
        clasificacion = "SERVICIOS BASICOS"
    return {"institucion": institucion_final, "estructura_programatica": estructura_final, "numero_libramiento": libramiento_final, "importe": importe_final, "clasificacion": clasificacion}

# ================= ENTRADA =================
texto_pegado = st.text_area("📥 Pegue el texto aquí")
if st.button("📤 Enviar al Historial"):
    if texto_pegado.strip():
        nuevo_registro = extraer_datos(texto_pegado)
        cursor.execute("INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion) VALUES (?, ?, ?, ?, ?)", (nuevo_registro["institucion"], nuevo_registro["estructura_programatica"], nuevo_registro["numero_libramiento"], nuevo_registro["importe"], nuevo_registro["clasificacion"]))
        conn.commit()
        if nuevo_registro["clasificacion"] == "SERVICIOS BASICOS":
            alerta = st.empty()
            alerta.success("🚀 CLASIFICACIÓN DETECTADA: BIENES Y SERVICIOS")
            time.sleep(3)
            alerta.empty()
        st.rerun()

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial")
df_historial = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", conn)
if not df_historial.empty:
    st.dataframe(df_historial, use_container_width=True, hide_index=True)

# ================= SELECTOR DE EXPEDIENTE =================
registro_sel = None
if not df_historial.empty:
    def formato_seguro(x):
        fila = df_historial[df_historial["id"] == x]
        return f"Expediente #{x} — {fila.iloc[0]['institucion']}" if not fila.empty else f"#{x}"
    registro_sel = st.selectbox("📌 Seleccione expediente para trabajar:", df_historial["id"].tolist(), format_func=formato_seguro)

# ================= LÓGICA DE GUARDADO AUTOMÁTICO =================
def guardar_formulario_automatico(registro_id, datos_dict):
    """Sincroniza el estado del editor con la base de datos inmediatamente."""
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
    """, (registro_id, *datos_dict.values()))
    conn.commit()

def crear_formulario_bienes_servicios_auto(registro_id, en_uso=False):
    columnas = ["CC","CP","OFI","FACT","FIRMA_DIGITAL","Recep","RPE","DGII","TSS","OC",
                "CONT","TITULO","DETE","JURI_INMO","TASACION","APROB_PRESI","VIAJE_PRESI"]
    
    label_en_uso = '<span class="badge-en-uso">En uso</span>' if en_uso else ""
    st.markdown(f'### 📋 Bienes y Servicios {label_en_uso}', unsafe_allow_html=True)

    # Cargar datos existentes
    df_db = pd.read_sql_query(f"SELECT * FROM formulario_bienes_servicios WHERE registro_id={registro_id}", conn)
    
    if df_db.empty:
        df_actual = pd.DataFrame([{col: "√" for col in columnas}])
    else:
        df_actual = df_db[columnas]

    config = {col: st.column_config.SelectboxColumn(options=["√","N/A"], width=65) for col in columnas}
    
    # Renderizar editor y detectar cambios al instante
    df_editado = st.data_editor(df_actual, column_config=config, hide_index=True, key=f"editor_auto_{registro_id}")

    # GUARDADO AUTOMÁTICO: Si los datos en pantalla difieren de los de la base de datos
    if not df_editado.equals(df_actual):
        guardar_formulario_automatico(registro_id, df_editado.iloc[0].to_dict())
        st.toast(f"☁️ Cambios en Expediente #{registro_id} guardados automáticamente")

# ================= RENDERIZADO =================
st.markdown("---")
if registro_sel:
    fila_sel = df_historial[df_historial["id"] == registro_sel]
    es_sb = fila_sel.iloc[0]["clasificacion"] == "SERVICIOS BASICOS" if not fila_sel.empty else False
    crear_formulario_bienes_servicios_auto(registro_sel, en_uso=es_sb)

# Los demás formularios se mantienen como visuales hasta que necesites ligarlos
def crear_formulario_estatico(titulo, columnas, clave):
    st.markdown(f"### 📋 {titulo}")
    df = pd.DataFrame([{col: "√" for col in columnas}])
    config = {col: st.column_config.SelectboxColumn(options=["√", "N/A"], width=65) for col in columnas}
    st.data_editor(df, column_config=config, hide_index=True, key=clave)

crear_formulario_estatico("Transferencias", ["OFI", "FIRMA DIGITAL", "PRES", "OFIC", "BENE", "NÓMINA", "CARTA RUTA", "RNC", "MERCADO VA", "DECRETO", "CONGRESO", "DIR. FIDE", "CONTR. FIDU", "DEUDA EXT", "ANTICIPO"], "f_t")
crear_formulario_estatico("Obras", ["CC", "CP", "OFI", "FIRMA DIGITAL", "FACT", "Recep", "RPE", "DGII", "TSS", "OC", "CONT", "EVATEC", "CU", "SUP", "Cierre de Obra", "20%", "AVA", "FIEL"], "f_o")
