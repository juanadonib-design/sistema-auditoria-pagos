import streamlit as st
import pandas as pd
import re

st.title("Sistema de apoyo para auditoría de pagos")

texto = st.text_area("Pega aquí el texto del expediente")

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


if texto:
    registro = extraer_datos(texto)
    df = pd.DataFrame([registro])
    st.subheader("Vista previa de datos")
    st.dataframe(df)
