import streamlit as st
import pandas as pd
import re
import sqlite3

st.set_page_config(layout="wide")
st.title("🧾 Sistema de Apoyo para Auditoría de Pagos")

# ================= BASE DE DATOS =================
conn = sqlite3.connect("auditoria.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    institucion TEXT,
    estructura_programatica TEXT,
    numero_libramiento TEXT UNIQUE,
    importe TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS formulario_bienes_servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificacion TEXT,
    cuota TEXT,
    comprometer TEXT,
    orden_compra TEXT,
    factura TEXT,
    recepcion TEXT
)
""")
conn.commit()

# ================= EXTRAER DATOS DEL TEXTO =================
def extraer_datos(texto):
    inst = re.search(r'(Ministerio|Dirección|Instituto|Oficina)[^\n]+', texto)
    est = re.search(r'\b\d{12}\b', texto)
    lib = re.search(r'\b\d{1,5}\b', texto)
    imp = re.search(r'(RD\$|\$)\s?[\d,]+(\.\d{2})?', texto)

    return {
        "Institucion": inst.group(0) if inst else "",
        "Estructura Programatica": est.group(0) if est else "",
        "Numero Libramiento": lib.group(0) if lib else "",
        "Importe": imp.group(0) if imp else ""
    }

# ================= GUARDAR REGISTRO =================
def guardar_registro(datos):
    try:
        cursor.execute("""
        INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe)
        VALUES (?, ?, ?, ?)
        """, (
            datos["Institucion"],
            datos["Estructura Programatica"],
            datos["Numero Libramiento"],
            datos["Importe"]
        ))
        conn.commit()
    except:
        pass

# ================= INTERFAZ TEXTO =================
texto = st.text_area("📄 Pegue el texto del documento aquí")

if st.button("Procesar información"):
    registro = extraer_datos(texto)
    guardar_registro(registro)
    st.success("Registro guardado automáticamente")

# ================= HISTORIAL =================
st.subheader("📁 Historial de registros almacenados")
df_historial = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", conn)
st.dataframe(df_historial)

# ================= EXPORTAR EXCEL =================
st.subheader("⬇️ Exportar historial a Excel")
if not df_historial.empty:
    archivo_excel = "historial_auditoria.xlsx"
    df_historial.to_excel(archivo_excel, index=False)

    with open(archivo_excel, "rb") as file:
        st.download_button(
            label="Descargar archivo Excel",
            data=file,
            file_name="historial_auditoria.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ================= FORMULARIO BIENES Y SERVICIOS =================
st.subheader("📋 Formulario de Bienes y Servicios")

def fila_documento(nombre):
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            f"""
            <div style="
                font-weight: 600;
                line-height: 1.1;
                word-wrap: break-word;
                white-space: normal;
                font-size: 14px;
            ">
                {"<br>".join(nombre.split())}
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        return st.selectbox(" ", ["√", "N/A"], key=nombre)

certificacion = fila_documento("Certificacion Cuota Comprometer")
orden = fila_documento("Orden Compra")
factura = fila_documento("Factura")
recepcion = fila_documento("Recepcion Bienes Servicios")

if st.button("Guardar Formulario"):
    cursor.execute("""
    INSERT INTO formulario_bienes_servicios (certificacion, cuota, comprometer, orden_compra, factura, recepcion)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (certificacion, certificacion, certificacion, orden, factura, recepcion))
    conn.commit()
    st.success("Formulario guardado")

# ================= HISTORIAL FORMULARIO =================
st.subheader("📂 Historial Formularios")
df_form = pd.read_sql_query("SELECT * FROM formulario_bienes_servicios ORDER BY id DESC", conn)
st.dataframe(df_form)
