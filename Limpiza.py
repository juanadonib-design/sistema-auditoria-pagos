import sqlite3

conn = sqlite3.connect("auditoria.db")
cursor = conn.cursor()

# Borra el contenido de las tablas, pero deja la estructura
cursor.execute("DELETE FROM usuarios")
cursor.execute("DELETE FROM registros")
cursor.execute("DELETE FROM formulario_bienes_servicios")

# Reinicia los contadores de ID para que empiecen en 1 otra vez
cursor.execute("DELETE FROM sqlite_sequence WHERE name='usuarios'")
cursor.execute("DELETE FROM sqlite_sequence WHERE name='registros'")
cursor.execute("DELETE FROM sqlite_sequence WHERE name='formulario_bienes_servicios'")

conn.commit()
conn.close()

print("Base de datos vaciada correctamente.")