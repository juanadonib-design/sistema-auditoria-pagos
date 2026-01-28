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

# ================= ENTRADA =================
texto = st.text_area("📥 Pegue el texto del documento aquí")

if st.button("🔍 Analizar texto"):
    registro = extraer_datos(texto)
    st.dataframe(pd.DataFrame([registro]))
    guardar_registro(registro)
    st.success("Registro guardado")

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial de Registros")
df_historial = pd.read_sql_query("SELECT * FROM registros", conn)
st.dataframe(df_historial)

if not df_historial.empty:
    df_historial.to_excel("historial_auditoria.xlsx", index=False)
    with open("historial_auditoria.xlsx", "rb") as file:
        st.download_button("⬇️ Descargar Historial Excel", file, "historial_auditoria.xlsx")

# ================= FORMULARIO OPTIMIZADO =================
st.markdown("---")
st.header("📋 Formulario de Verificación — Bienes y Servicios")

# Diccionario de mapeo: Nombre Original vs Nombre Corto para la Columna
columnas_map = {
    "Certificación de Cuota a Comprometer": "Cert. Cuota",
    "Certificado de Apropiacion Presupuestario": "Cert. Presup.",
    "Oficio de Autorización": "Oficio Aut.",
    "Factura": "Factura",
    "Validación Firma Digital": "Firma Dig.",
    "Recepción": "Recepción",
    "RPE": "RPE",
    "DGII": "DGII",
    "TSS": "TSS",
    "Orden de Compra": "Ord. Compra",
    "Contrato": "Contrato",
    "Título de Propiedad": "Título Prop.",
    "Determinación": "Determ.",
    "Estado Jurídico del Inmueble": "Est. Juríd.",
    "Tasación": "Tasación",
    "Aprobación Ministerio de la Presidencia": "Aprob. Min.",
    "Viaje Presidencial": "Viaje Pres."
}

# Creamos el DataFrame usando las llaves largas (nombres reales)
columnas_reales = list(columnas_map.keys())
df_formulario = pd.DataFrame([{col: "√" for col in columnas_reales}])

# Configuración de columnas para forzar el ajuste visual
config_columnas = {
    original: st.column_config.SelectboxColumn(
        label=corto,           # Nombre que se muestra (corto)
        help=original,         # Nombre completo al pasar el mouse
        options=["√", "N/A"],
        width=85,              # Ancho reducido
        required=True
    ) for original, corto in columnas_map.items()
}

# Editor de datos con ancho controlado
tabla_editable = st.data_editor(
    df_formulario,
    column_config=config_columnas,
    use_container_width=False, 
    num_rows="fixed",
    hide_index=True
)

# ================= VALIDACIÓN =================
fila = tabla_editable.iloc[0]
faltantes = [col for col in columnas_reales if fila[col] == "N/A"]
expediente_completo = "Sí" if len(faltantes) == 0 else "No"

st.write(f"### Expediente Completo: **{expediente_completo}**")

if faltantes:
    st.warning("⚠️ Elementos marcados como N/A:")
    for f in faltantes:
        st.write(f"• {f}")

# ================= GUARDAR Y DESCARGAR =================
if st.button("💾 Guardar Formulario"):
    df_guardar = tabla_editable.copy()
    df_guardar["Expediente Completo"] = expediente_completo

    archivo = "formulario_bienes_servicios.xlsx"
    try:
        df_existente = pd.read_excel(archivo)
        df_final = pd.concat([df_existente, df_guardar], ignore_index=True)
    except:
        df_final = df_guardar

    df_final.to_excel(archivo, index=False)
    st.success("Formulario guardado en Excel")

try:
    with open("formulario_bienes_servicios.xlsx", "rb") as f:
        st.download_button("⬇️ Descargar Formularios Excel", f, "formulario_bienes_servicios.xlsx")
except:
    st.info("Aún no hay formularios guardados")
