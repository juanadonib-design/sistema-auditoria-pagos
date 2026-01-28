import streamlit as st
import pandas as pd
import re
import sqlite3

st.set_page_config(page_title="Sistema Auditoría de Pagos", layout="wide")

# === TRUCO DE CSS PARA AJUSTAR TEXTO EN ENCABEZADOS ===
st.markdown("""
    <style>
        /* Forzar que el texto de los encabezados de la tabla se ajuste (Wrap) */
        div[data-testid="stDataEditor"] div[class^="st-"] th {
            white-space: normal !important;
            word-wrap: break-word !important;
            line-height: 1.2 !important;
            height: auto !important;
            min-height: 80px !important;
            vertical-align: middle !important;
        }
        /* Ajuste específico para el contenedor del data_editor */
        [data-testid="stDataEditor"] [class^="st-"] {
            line-height: 1.2;
        }
    </style>
""", unsafe_allow_html=True)

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

# ... (Tus funciones guardar_registro y extraer_datos se mantienen igual) ...
def guardar_registro(datos):
    cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe)
        VALUES (?, ?, ?, ?)
    """, (datos["Institucion"], datos["Estructura"], datos["Libramiento"], datos["Importe"]))
    conn.commit()

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

# ================= ENTRADA Y ANALISIS =================
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

# ================= FORMULARIO CON AJUSTE DE TEXTO =================
st.markdown("---")
st.header("📋 Formulario de Verificación — Bienes y Servicios")

columnas_formulario = [
    "Certificación de Cuota a Comprometer",
    "Certificado de Apropiacion Presupuestario",
    "Oficio de Autorización",
    "Factura",
    "Validación Firma Digital",
    "Recepción",
    "RPE",
    "DGII",
    "TSS",
    "Orden de Compra",
    "Contrato",
    "Título de Propiedad",
    "Determinación",
    "Estado Jurídico del Inmueble",
    "Tasación",
    "Aprobación Ministerio de la Presidencia",
    "Viaje Presidencial"
]

df_formulario = pd.DataFrame([{col: "√" for col in columnas_formulario}])

# Configuración: Ahora sí respetará el ancho de 85px y el texto bajará
config_columnas = {
    col: st.column_config.SelectboxColumn(
        label=col, 
        options=["√", "N/A"],
        width=85,  # Ancho pequeño, el CSS hará el resto
        required=True
    ) for col in columnas_formulario
}

tabla_editable = st.data_editor(
    df_formulario,
    column_config=config_columnas,
    use_container_width=False,
    num_rows="fixed",
    hide_index=True
)

# ================= VALIDACIÓN Y GUARDADO =================
fila = tabla_editable.iloc[0]
faltantes = [col for col in columnas_formulario if fila[col] == "N/A"]
expediente_completo = "Sí" if len(faltantes) == 0 else "No"
st.write(f"### Expediente Completo: **{expediente_completo}**")

if st.button("💾 Guardar Formulario"):
    df_guardar = tabla_editable.copy()
    df_guardar["Expediente Completo"] = expediente_completo
    df_guardar.to_excel("formulario_bienes_servicios.xlsx", index=False)
    st.success("Formulario guardado")
