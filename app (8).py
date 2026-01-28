import streamlit as st
import pandas as pd
import re
import sqlite3

st.title("Sistema de apoyo para auditoría de pagos")

# ================= BASE DE DATOS =================
conn = sqlite3.connect("auditoria_pagos.db", check_same_thread=False)
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
conn.commit()

# ================= FUNCION EXTRAER DATOS =================
def extraer_datos(texto):
    datos = {}

    inst = re.search(
        r'Instituci[oó]n\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]+?)(?=\s+Estructura|\s+Libramiento|\s+No\.?|\s+RD\$|\s+\$|$)',
        texto
    )
    datos["Institucion"] = inst.group(1).strip() if inst else None

    est = re.search(r'\b\d{12}\b', texto)
    datos["Estructura programatica"] = est.group() if est else None

    lib = re.search(r'(Libramiento|No\.?)\s*(\d{1,5})\b', texto)
    datos["Numero de libramiento"] = lib.group(2) if lib else None

    imp = re.search(r'(RD\$|\$)\s?[\d,]+\.\d{2}', texto)
    datos["Importe"] = imp.group() if imp else None

    return datos

# ================= GUARDAR AUTOMATICAMENTE =================
def guardar_registro(datos):
    try:
        cursor.execute("""
            INSERT INTO registros (institucion, estructura_programatica, numero_libramiento, importe)
            VALUES (?, ?, ?, ?)
        """, (
            datos["Institucion"],
            datos["Estructura programatica"],
            datos["Numero de libramiento"],
            datos["Importe"]
        ))
        conn.commit()
        st.success("Registro guardado automáticamente")
    except sqlite3.IntegrityError:
        st.info("Este registro ya existe en la base de datos")

# ================= INTERFAZ =================
texto = st.text_area("Pega aquí el texto del expediente")

if texto:
    registro = extraer_datos(texto)
    df = pd.DataFrame([registro])

    st.subheader("Vista previa de datos")
    st.dataframe(df)

    if registro["Numero de libramiento"]:
        guardar_registro(registro)

# ================= CONTADOR =================
cursor.execute("SELECT COUNT(*) FROM registros")
total = cursor.fetchone()[0]
st.write(f"📊 Total de registros almacenados: {total}")

# ================= HISTORIAL =================
st.subheader("📁 Historial de registros almacenados")
df_historial = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", conn)
st.dataframe(df_historial)
