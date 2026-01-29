import streamlit as st
import pandas as pd
import re
import sqlite3
import time

# Configuración de página
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

# ================= CONEXIÓN Y ESTRUCTURA DE BD =================
def ejecutar_query(query, params=(), commit=False):
    with sqlite3.connect("auditoria.db", check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
        return cursor.fetchall()

# Crear tablas
ejecutar_query("CREATE TABLE IF NOT EXISTS registros (id INTEGER PRIMARY KEY AUTOINCREMENT, institucion TEXT, estructura_programatica TEXT, numero_libramiento TEXT, importe TEXT, clasificacion TEXT)", commit=True)
ejecutar_query("""
CREATE TABLE IF NOT EXISTS formulario_bienes_servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registro_id INTEGER UNIQUE,
    CC TEXT, CP TEXT, OFI TEXT, FACT TEXT, FIRMA_DIGITAL TEXT, Recep TEXT,
    RPE TEXT, DGII TEXT, TSS TEXT, OC TEXT, CONT TEXT, TITULO TEXT,
    DETE TEXT, JURI_INMO TEXT, TASACION TEXT, APROB_PRESI TEXT, VIAJE_PRESI TEXT,
    FOREIGN KEY(registro_id) REFERENCES registros(id)
)
""", commit=True)

# ================= LÓGICA DE BORRADO ROBUSTA (SOLUCIÓN DEFINITIVA) =================
if "editor_principal" in st.session_state:
    changes = st.session_state["editor_principal"]
    if changes.get("deleted_rows"):
        # Cargamos los IDs actuales de la base de datos para mapear el índice del editor
        res = ejecutar_query("SELECT id FROM registros ORDER BY id DESC")
        if res:
            ids_actuales = [row[0] for row in res]
            indices_a_borrar = changes["deleted_rows"]
            
            for idx in indices_a_borrar:
                if idx < len(ids_actuales):
                    id_real = ids_actuales[idx]
                    # Borramos con validación de tipo
                    if id_real is not None:
                        ejecutar_query("DELETE FROM formulario_bienes_servicios WHERE registro_id = ?", (int(id_real),), commit=True)
                        ejecutar_query("DELETE FROM registros WHERE id = ?", (int(id_real),), commit=True)
            
            # Limpiamos el estado para evitar que el bucle se repita al recargar
            st.session_state["editor_principal"]["deleted_rows"] = []
            st.toast("🗑️ Registro eliminado correctamente")
            time.sleep(0.5)
            st.rerun()

# ================= EXTRACCIÓN =================
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

# ================= ENTRADA =================
texto_pegado = st.text_area("📥 Pegue el texto aquí")
if st.button("📤 Enviar al Historial"):
    if texto_pegado.strip():
        d = extraer_datos(texto_pegado)
        ejecutar_query("INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe, clasificacion) VALUES (?, ?, ?, ?, ?)", 
                       (d["institucion"], d["estructura"], d["libramiento"], d["importe"], d["clasificacion"]), commit=True)
        st.rerun()

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial")
res_h = ejecutar_query("SELECT * FROM registros ORDER BY id DESC")
df_h = pd.DataFrame(res_h, columns=["id", "institucion", "estructura_programatica", "numero_libramiento", "importe", "clasificacion"])

if not df_h.empty:
    st.data_editor(df_h, use_container_width=True, hide_index=True, num_rows="dynamic", key="editor_principal")
else:
    st.info("No hay registros.")

# ================= SELECTOR SEGURO =================
st.markdown("---")
registro_sel = None
if not df_h.empty:
    opciones = df_h["id"].tolist()
    registro_sel = st.selectbox(
        "📌 Seleccione expediente para trabajar:", 
        opciones, 
        format_func=lambda x: f"ID #{x} - {df_h[df_h['id']==x]['institucion'].values[0]}" if not df_h[df_h['id']==x].empty else f"#{x}"
    )

# ================= FORMULARIOS =================
def crear_formulario_bienes_servicios(reg_id, en_uso=False):
    # Verificamos si el registro sigue existiendo antes de renderizar
    check = ejecutar_query("SELECT id FROM registros WHERE id = ?", (reg_id,))
    if not check:
        return

    columnas = ["CC","CP","OFI","FACT","FIRMA_DIGITAL","Recep","RPE","DGII","TSS","OC","CONT","TITULO","DETE","JURI_INMO","TASACION","APROB_PRESI","VIAJE_PRESI"]
    if en_uso:
        st.markdown(f'### 📋 Bienes y Servicios <span class="badge-en-uso">En uso</span>', unsafe_allow_html=True)
    else:
        st.markdown("### 📋 Bienes y Servicios")

    res_f = ejecutar_query(f"SELECT CC, CP, OFI, FACT, FIRMA_DIGITAL, Recep, RPE, DGII, TSS, OC, CONT, TITULO, DETE, JURI_INMO, TASACION, APROB_PRESI, VIAJE_PRESI FROM formulario_bienes_servicios WHERE registro_id={reg_id}")
    df_f = pd.DataFrame(res_f, columns=columnas) if res_f else pd.DataFrame([{c:"√" for c in columnas}])

    df_edit = st.data_editor(df_f, column_config={c: st.column_config.SelectboxColumn(options=["√","N/A"], width=65) for c in columnas}, hide_index=True, key=f"f_{reg_id}")

    if st.button("💾 Guardar Formulario", key=f"b_{reg_id}"):
        vals = df_edit.iloc[0].tolist()
        ejecutar_query("""
            INSERT INTO formulario_bienes_servicios (registro_id, CC, CP, OFI, FACT, FIRMA_DIGITAL, Recep, RPE, DGII, TSS, OC, CONT, TITULO, DETE, JURI_INMO, TASACION, APROB_PRESI, VIAJE_PRESI)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(registro_id) DO UPDATE SET CC=excluded.CC, CP=excluded.CP, OFI=excluded.OFI, FACT=excluded.FACT, FIRMA_DIGITAL=excluded.FIRMA_DIGITAL, Recep=excluded.Recep, RPE=excluded.RPE, DGII=excluded.DGII, TSS=excluded.TSS, OC=excluded.OC, CONT=excluded.CONT, TITULO=excluded.TITULO, DETE=excluded.DETE, JURI_INMO=excluded.JURI_INMO, TASACION=excluded.TASACION, APROB_PRESI=excluded.APROB_PRESI, VIAJE_PRESI=excluded.VIAJE_PRESI
        """, (reg_id, *vals), commit=True)
        st.success(f"Formulario #{reg_id} guardado.")

if registro_sel:
    fila_sel = df_h[df_h["id"]==registro_sel]
    if not fila_sel.empty:
        es_sb = fila_sel["clasificacion"].values[0] == "SERVICIOS BASICOS"
        crear_formulario_bienes_servicios(registro_sel, en_uso=es_sb)

st.subheader("📋 Transferencias")
st.data_editor(pd.DataFrame([{"OFI":"√"}]), hide_index=True, key="t")
st.subheader("📋 Obras")
st.data_editor(pd.DataFrame([{"CC":"√"}]), hide_index=True, key="o")
