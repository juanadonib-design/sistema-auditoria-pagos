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

# ================= EXTRACCIÓN DE DATOS =================
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

# ================= ENTRADA DE TEXTO =================
texto = st.text_area("📥 Pegue el texto del documento aquí")

if st.button("🔍 Analizar texto"):
    registro = extraer_datos(texto)
    st.write("### Vista previa")
    df_preview = pd.DataFrame([registro])
    st.dataframe(df_preview)

    guardar_registro(registro)
    st.success("Registro guardado automáticamente")

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial de Registros")

df_historial = pd.read_sql_query("SELECT * FROM registros", conn)
st.dataframe(df_historial)

st.write(f"Total registros almacenados: {len(df_historial)} / 15,000")

# ================= EXPORTAR HISTORIAL =================
if not df_historial.empty:
    archivo_excel = "historial_auditoria.xlsx"
    df_historial.to_excel(archivo_excel, index=False)
    with open(archivo_excel, "rb") as file:
        st.download_button(
            label="⬇️ Descargar Historial en Excel",
            data=file,
            file_name="historial_auditoria.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ================= FORMULARIO BIENES Y SERVICIOS =================
st.markdown("---")
st.header("📋 Formulario de Verificación — Bienes y Servicios")

def opcion(label):
    return st.selectbox(label, ["Sí", "No"], key="form_" + label)

datos_formulario = {
    "Certificación Cuota Comprometer": opcion("Certificación Cuota Comprometer"),
    "Certificación Apropiación Presupuestaria": opcion("Certificación Apropiación Presupuestaria"),
    "Oficio de Autorización": opcion("Oficio de Autorización"),
    "Factura": opcion("Factura"),
    "Validación Firma Digital": opcion("Validación Firma Digital"),
    "Recepción": opcion("Recepción"),
    "RPE": opcion("RPE"),
    "DGI": opcion("DGI"),
    "TSS": opcion("TSS"),
    "Orden de Compra": opcion("Orden de Compra"),
    "Contrato": opcion("Contrato"),
    "Título de Propiedad": opcion("Título de Propiedad"),
    "Determinación": opcion("Determinación"),
    "Estado Jurídico del Inmueble": opcion("Estado Jurídico del Inmueble"),
    "Tasación": opcion("Tasación"),
    "Aprobación Ministerio de la Presidencia": opcion("Aprobación Ministerio de la Presidencia"),
    "Viaje Presidencial": opcion("Viaje Presidencial"),
}

# ================= GUARDAR FORMULARIO =================
if st.button("💾 Guardar Formulario"):
    df_form = pd.DataFrame([datos_formulario])
    archivo = "formulario_bienes_servicios.xlsx"

    try:
        df_existente = pd.read_excel(archivo)
        df_final = pd.concat([df_existente, df_form], ignore_index=True)
    except:
        df_final = df_form

    df_final.to_excel(archivo, index=False)
    st.success("Formulario guardado en Excel")

# ================= VALIDACIÓN =================
faltantes = [k for k, v in datos_formulario.items() if v == "No"]

if faltantes:
    st.warning("⚠️ Documentos faltantes:")
    for f in faltantes:
        st.write("•", f)
else:
    st.success("✅ Expediente completo")

# ================= DESCARGAR FORMULARIOS =================
try:
    with open("formulario_bienes_servicios.xlsx", "rb") as f:
        st.download_button(
            "⬇️ Descargar Formularios Excel",
            f,
            file_name="formulario_bienes_servicios.xlsx"
        )
except:
    st.info("Aún no hay formularios guardados")
