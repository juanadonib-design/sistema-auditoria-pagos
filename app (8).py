import re
import pandas as pd

def extraer_datos(texto):
    datos = {}

    # 🔹 Institución
    inst = re.search(r'Instituci[oó]n\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]+)', texto)
    if inst:
        datos["Institucion"] = inst.group(1).strip()
    else:
        datos["Institucion"] = None

    # 🔹 Estructura programática (12 dígitos)
    est = re.search(r'\b\d{12}\b', texto)
    if est:
        datos["Estructura programatica"] = est.group()
    else:
        datos["Estructura programatica"] = None

    # 🔹 Número de libramiento (1 a 5 dígitos)
    lib = re.search(r'(Libramiento|libramiento|No\.?)\s*(\d{1,5})\b', texto)
    if lib:
        datos["Numero de libramiento"] = lib.group(2)
    else:
        datos["Numero de libramiento"] = None

    # 🔹 Importe
    imp = re.search(r'(RD\$|\$)\s?[\d,]+\.\d{2}', texto)
    if imp:
        datos["Importe"] = imp.group()
    else:
        datos["Importe"] = None

    return datos

# Extraer datos
registro = extraer_datos(texto)

# 📊 Crear vista tipo Excel
df = pd.DataFrame([registro])

print("\n===== VISTA PREVIA DE DATOS =====")
print(df)

