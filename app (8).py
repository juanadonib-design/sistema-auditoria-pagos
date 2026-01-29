import streamlit as st
import pandas as pd
import re
import sqlite3
import time

# 1. Configuración de la página
st.set_page_config(page_title="Sistema Auditoría", layout="wide")

# 2. Conexión estandarizada a la base de datos
def get_db_connection():
    conn = sqlite3.connect("auditoria.db", check_same_thread=False)
    return conn

# Crear tablas si no existen
conn = get_db_connection()
cursor = conn.cursor()
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

# 3. Estilos CSS
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

# 4. Lógica de Extracción
def extraer_datos(texto):
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    inst, est, lib, imp, clas = "No encontrado", "No encontrado", "No encontrado", "No encontrado", "General"
    for i, linea in enumerate(lineas):
        if re.search(r'\bINSTITUCI[ÓO]N\b', linea, re.IGNORECASE):
            if i + 1 < len(lineas): inst = lineas[i+1]
        elif re.search(r'\b(MINISTERIO|INABIE|DIRECCION|ALCALDIA|AYUNTAMIENTO)\b', linea, re.IGNORECASE):
            if inst == "No encontrado": inst = linea
    est_m = re.search(r'\b\d{12}\b', texto)
    if est_m: est = est_m.group(0)
    lib_m = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    lib = lib_m.group(1) if lib_m else (re.search(r'\b\d{1,6}\b', texto).group(0) if re.search(r'\b\d{1,6}\b', texto) else "No encontrado")
    imp_m = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    if imp_m: imp = imp_m.group(0)
    if "SERVICIOS BASICOS" in texto.upper() or "SERVICIO BASICO" in texto.upper(): clas = "SERVICIOS BASICOS"
    return {"institucion": inst, "estructura": est, "libramiento": lib, "importe": imp, "clasificacion": clas}

# 5. Interfaz de Entrada
st.title("🧾 Sistema de Apoyo a la Auditoría de Pagos")
texto_pegado = st.text_area("📥 Pegue el texto aquí", height=150)

if st.button("📤 Enviar al Historial"):
    if texto_pegado.strip():
        d = extraer_datos(texto_pegado)
        cursor.execute("INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion) VALUES (?, ?, ?, ?, ?)", 
                       (d["institucion"], d["estructura"], d["libramiento"], d["importe"], d["clasificacion"]))
        conn.commit()
        if d["clasificacion"] == "SERVICIOS BASICOS":
            st.success("🚀 CLASIFICACIÓN DETECTADA: BIENES Y SERVICIOS")
            time.sleep(2)
        st.rerun()

# 6. Historial con Borrado Definitivo
st.markdown("---")
st.subheader("📊 Historial")

# Siempre leer datos actualizados de la DB
df_historial = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", conn)

if not df_historial.empty:
    # Si detectamos que el usuario borró filas en la interfaz
    editor_key = "historial_principal"
    df_editado = st.data_editor(df_historial, use_container_width=True, hide_index=True, num_rows="dynamic", key=editor_key)

    # LÓGICA DE BORRADO REAL
    if len(df_editado) < len(df_historial):
        ids_vivos = df_editado["id"].tolist()
        ids_en_db = df_historial["id"].tolist()
        ids_para_borrar = [i for i in ids_en_db if i not in ids_vivos]
        
        for id_del in ids_para_borrar:
            cursor.execute("DELETE FROM formulario_bienes_servicios WHERE registro_id = ?", (id_del,))
            cursor.execute("DELETE FROM registros WHERE id = ?", (id_del,))
        conn.commit()
        st.toast("🗑️ Eliminado de la base de datos")
        time.sleep(0.5)
        st.rerun()
else:
    st.info("No hay registros en el historial.")

# 7. Selector y Formulario
st.markdown("---")
if not df_historial.empty:
    registro_sel = st.selectbox(
        "📌 Seleccione expediente para trabajar:", 
        df_historial["id"].tolist(), 
        format_func=lambda x: f"ID #{x} - {df_historial[df_historial['id']==x]['institucion'].values[0]}" if not df_historial[df_historial['id']==x].empty else f"#{x}"
    )

    if registro_sel:
        # Verificar que el ID seleccionado no haya sido borrado
        check = pd.read_sql_query(f"SELECT * FROM registros WHERE id={registro_sel}", conn)
        if not check.empty:
            es_sb = check.iloc[0]["clasificacion"] == "SERVICIOS BASICOS"
            label_uso = '<span class="badge-en-uso">En uso</span>' if es_sb else ""
            st.markdown(f'### 📋 Bienes y Servicios {label_uso}', unsafe_allow_html=True)

            col_form = ["CC","CP","OFI","FACT","FIRMA_DIGITAL","Recep","RPE","DGII","TSS","OC","CONT","TITULO","DETE","JURI_INMO","TASACION","APROB_PRESI","VIAJE_PRESI"]
            res_f = pd.read_sql_query(f"SELECT * FROM formulario_bienes_servicios WHERE registro_id={registro_sel}", conn)
            
            df_f = res_f[col_form] if not res_f.empty else pd.DataFrame([{c:"√" for c in col_form}])
            df_edit = st.data_editor(df_f, hide_index=True, key=f"form_{registro_sel}")

            if st.button("💾 Guardar Formulario"):
                v = df_edit.iloc[0].tolist()
                cursor.execute("""
                    INSERT INTO formulario_bienes_servicios (registro_id, CC, CP, OFI, FACT, FIRMA_DIGITAL, Recep, RPE, DGII, TSS, OC, CONT, TITULO, DETE, JURI_INMO, TASACION, APROB_PRESI, VIAJE_PRESI)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(registro_id) DO UPDATE SET CC=excluded.CC, CP=excluded.CP, OFI=excluded.OFI, FACT=excluded.FACT, FIRMA_DIGITAL=excluded.FIRMA_DIGITAL, Recep=excluded.Recep, RPE=excluded.RPE, DGII=excluded.DGII, TSS=excluded.TSS, OC=excluded.OC, CONT=excluded.CONT, TITULO=excluded.TITULO, DETE=excluded.DETE, JURI_INMO=excluded.JURI_INMO, TASACION=excluded.TASACION, APROB_PRESI=excluded.APROB_PRESI, VIAJE_PRESI=excluded.VIAJE_PRESI
                """, (registro_sel, *v))
                conn.commit()
                st.success("Guardado correctamente.")
