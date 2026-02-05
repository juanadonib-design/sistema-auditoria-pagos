import streamlit as st
import pandas as pd
import re
import time
import unicodedata
from io import BytesIO
import hashlib
from sqlalchemy import text

# ================= CONFIGURACIÓN INICIAL =================
st.set_page_config(page_title="Sistema Auditoría de Pagos", layout="wide")

if "pantalla" not in st.session_state:
    st.session_state.pantalla = "login"

# ================= CONEXIÓN A BASE DE DATOS (SUPABASE) =================
conn = st.connection("supabase", type="sql")

def run_query(query_sql, params=None):
    try:
        with conn.session as session:
            if params:
                session.execute(text(query_sql), params)
            else:
                session.execute(text(query_sql))
            session.commit()
            return True
    except Exception as e:
        st.error(f"Error en base de datos: {e}")
        return False

def get_data(query_sql, params=None):
    return conn.query(query_sql, params=params, ttl=0)

# ================= CREACIÓN DE TABLAS =================
def inicializar_tablas():
    run_query("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            usuario TEXT UNIQUE,
            password TEXT
        );
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS registros (
            id SERIAL PRIMARY KEY,
            institucion TEXT,
            estructura_programatica TEXT,
            numero_libramiento TEXT,
            importe TEXT,
            clasificacion TEXT,
            rnc TEXT,
            cuenta_objetal TEXT,
            usuario_id INTEGER,
            estado TEXT DEFAULT 'En proceso'
        );
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS formulario_bienes_servicios (
            id SERIAL PRIMARY KEY,
            registro_id INTEGER UNIQUE,
            CC TEXT, CP TEXT, OFI TEXT, FACT TEXT, FIRMA_DIGITAL TEXT, Recep TEXT,
            RPE TEXT, DGII TEXT, TSS TEXT, OC TEXT, CONT TEXT, TITULO TEXT,
            DETE TEXT, JURI_INMO TEXT, TASACION TEXT, APROB_PRESI TEXT, VIAJE_PRESI TEXT
        );
    """)

def actualizar_db_exportado():
    try:
        run_query("ALTER TABLE registros ADD COLUMN IF NOT EXISTS exportado BOOLEAN DEFAULT FALSE;")
        run_query("UPDATE registros SET exportado = FALSE WHERE exportado IS NULL;")
    except Exception as e:
        pass 

inicializar_tablas()
actualizar_db_exportado()

# ================= FUNCIONES DE APOYO =================
def encriptar_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def extraer_datos(texto):
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    institucion_final = "No encontrado"
    estructura_final = "No encontrado"
    libramiento_final = "No encontrado"
    importe_final = "No encontrado"
    
    # --- LÓGICA DE CLASIFICACIÓN ---
    # 1. Empieza como General (para no mostrar formulario por error)
    clasificacion = "General"

    rnc_match = re.search(r'\b\d{9,11}\b', texto)
    rnc_final = rnc_match.group(0) if rnc_match else ""

    for i, linea in enumerate(lineas):
        if re.search(r'\bINSTITUCI[ÓO]N\b', linea, re.IGNORECASE):
            if i + 1 < len(lineas):
                institucion_final = lineas[i+1]
        elif re.search(r'\b(MINISTERIO|INABIE|DIRECCION|ALCALDIA|AYUNTAMIENTO)\b', linea, re.IGNORECASE):
            if institucion_final == "No encontrado":
                institucion_final = linea

    est_match = re.search(r'\b\d{12}\b', texto)
    if est_match: estructura_final = est_match.group(0)

    lib_match = re.search(r'(?:LIBRAMIENTO|NÚMERO|NO\.|Nº)\s*[:#-]?\s*(\b\d{1,10}\b)', texto, re.IGNORECASE)
    if lib_match: libramiento_final = lib_match.group(1)

    imp_match = re.search(r'RD\$?\s?[\d,]+\.\d{2}', texto)
    if imp_match: importe_final = imp_match.group(0)

    # 2. Si detecta palabras clave, cambia a SERVICIOS BASICOS
    texto_norm = unicodedata.normalize('NFD', texto.upper()).encode('ascii', 'ignore').decode('utf-8')
    
    patron_servicios = r'SERVICIOS?\s+BASICOS?'
    patron_bienes = r'BIENES\s+Y\s+SERVICIOS'

    if re.search(patron_servicios, texto_norm) or re.search(patron_bienes, texto_norm):
        clasificacion = "SERVICIOS BASICOS"

    return {
        "institucion": institucion_final,
        "estructura_programatica": estructura_final,
        "numero_libramiento": libramiento_final,
        "importe": importe_final,
        "clasificacion": clasificacion,
        "rnc": rnc_final
    }

# ================= DEFINICIÓN DEL FORMULARIO =================
def crear_formulario_bienes_servicios(registro_id):
    st.markdown('### 📋 Formulario de Bienes y Servicios <span class="badge-en-uso">En uso</span>', unsafe_allow_html=True)

    columnas = ["CC","CP","OFI","FACT","FIRMA_DIGITAL","Recep","RPE","DGII","TSS",
                "OC","CONT","TITULO","DETE","JURI_INMO","TASACION","APROB_PRESI","VIAJE_PRESI"]

    # 1. Obtener el RNC
    rnc_sql = "SELECT rnc FROM registros WHERE id = :id"
    df_rnc = get_data(rnc_sql, params={"id": int(registro_id)})
    
    if df_rnc.empty:
        st.error("Error cargando RNC")
        return

    rnc = str(df_rnc.iloc[0]["rnc"])

    # 2. BUSCAR SI YA EXISTE
    form_sql = "SELECT * FROM formulario_bienes_servicios WHERE registro_id = :rid"
    df_previo = get_data(form_sql, params={"rid": int(registro_id)})

    # 3. Inicialización
    if "form_bs" not in st.session_state or st.session_state.get("form_id") != registro_id:
        if not df_previo.empty:
            data_dict = df_previo.iloc[0].to_dict()
            filtered_data = {k: data_dict[k] for k in columnas if k in data_dict}
            st.session_state.form_bs = pd.DataFrame([filtered_data])
        else:
            base = {col: "N/A" for col in columnas}
            if rnc.startswith("1"):
                base.update({"OFI":"√","FACT":"√","RPE":"√","DGII":"√","TSS":"√"})
            elif rnc.startswith("4"):
                base.update({"OFI":"√","FACT":"√"})
            st.session_state.form_bs = pd.DataFrame([base])
        
        st.session_state.form_id = registro_id

    # 4. Botones de ayuda rápida
    if rnc.startswith("1") or rnc.startswith("4"):
        if st.button("✔ Marcar CC y CP"):
            st.session_state.form_bs.loc[0, ["CC","CP"]] = "√"
            
    if rnc.startswith("4"):
        if st.button("✔ Marcar DGII/TSS/RPE"):
            st.session_state.form_bs.loc[0, ["DGII","TSS","RPE"]] = "√"

    # 5. El Editor
    config = {col: st.column_config.SelectboxColumn(options=["√","N/A"], width=70) for col in columnas}
    
    df_editado = st.data_editor(
        st.session_state.form_bs, 
        column_config=config, 
        hide_index=True, 
        key="editor_bs"
    )

    # 6. Guardado
    if st.button("💾 Guardar Formulario"):
        datos = df_editado.iloc[0].to_dict()
        
        upsert_sql = """
            INSERT INTO formulario_bienes_servicios (
                registro_id, CC, CP, OFI, FACT, FIRMA_DIGITAL, Recep, RPE, DGII, TSS, 
                OC, CONT, TITULO, DETE, JURI_INMO, TASACION, APROB_PRESI, VIAJE_PRESI
            ) VALUES (
                :rid, :CC, :CP, :OFI, :FACT, :FIRMA_DIGITAL, :Recep, :RPE, :DGII, :TSS, 
                :OC, :CONT, :TITULO, :DETE, :JURI_INMO, :TASACION, :APROB_PRESI, :VIAJE_PRESI
            )
            ON CONFLICT (registro_id) DO UPDATE SET
                CC=EXCLUDED.CC, CP=EXCLUDED.CP, OFI=EXCLUDED.OFI, FACT=EXCLUDED.FACT,
                FIRMA_DIGITAL=EXCLUDED.FIRMA_DIGITAL, Recep=EXCLUDED.Recep, RPE=EXCLUDED.RPE,
                DGII=EXCLUDED.DGII, TSS=EXCLUDED.TSS, OC=EXCLUDED.OC, CONT=EXCLUDED.CONT,
                TITULO=EXCLUDED.TITULO, DETE=EXCLUDED.DETE, JURI_INMO=EXCLUDED.JURI_INMO,
                TASACION=EXCLUDED.TASACION, APROB_PRESI=EXCLUDED.APROB_PRESI, VIAJE_PRESI=EXCLUDED.VIAJE_PRESI;
        """
        
        params_form = datos.copy()
        params_form["rid"] = int(registro_id)
        
        if run_query(upsert_sql, params_form):
            run_query("UPDATE registros SET estado='Completado' WHERE id = :id", params={"id": int(registro_id)})
            st.success("Cambios guardados correctamente")
            time.sleep(0.5)
            st.rerun()

# 🔵 CSS
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

# ================= LOGIN / REGISTRO =================

if "usuario_id" not in st.session_state and st.session_state.pantalla == "login":
    st.title("🔐 Iniciar sesión (Nube)")
    user = st.text_input("Usuario", key="login_user")
    pwd  = st.text_input("Contraseña", type="password", key="login_pwd")

    if st.button("Ingresar"):
        user_clean = user.strip()
        pwd_clean = pwd.strip()
        sql = "SELECT id FROM usuarios WHERE usuario = :u AND password = :p"
        df_user = get_data(sql, params={"u": user_clean, "p": encriptar_password(pwd_clean)})

        if not df_user.empty:
            st.session_state.usuario_id = int(df_user.iloc[0]["id"])
            st.rerun()
        else:
            st.error("Datos incorrectos")

    if st.button("¿No tienes cuenta? Regístrate"):
        st.session_state.pantalla = "registro"
        st.rerun()
    st.stop()

if "usuario_id" not in st.session_state and st.session_state.pantalla == "registro":
    st.subheader("🆕 Crear cuenta")
    nuevo_nombre = st.text_input("Nombre completo", key="reg_nombre")
    nuevo_user   = st.text_input("Usuario", key="reg_user")
    nuevo_pwd    = st.text_input("Contraseña", type="password", key="reg_pwd")

    if st.button("➕ Crear cuenta"):
        if not nuevo_nombre or not nuevo_user or not nuevo_pwd:
            st.error("Todos los campos son obligatorios")
        else:
            check_sql = "SELECT id FROM usuarios WHERE usuario = :u"
            df_check = get_data(check_sql, params={"u": nuevo_user.strip()})
            if not df_check.empty:
                st.error("Ese usuario ya existe")
            else:
                insert_sql = "INSERT INTO usuarios (nombre, usuario, password) VALUES (:n, :u, :p)"
                params = {
                    "n": nuevo_nombre.strip(),
                    "u": nuevo_user.strip(),
                    "p": encriptar_password(nuevo_pwd.strip())
                }
                if run_query(insert_sql, params):
                    st.success("Cuenta creada correctamente")
                    time.sleep(1)
                    st.session_state.pantalla = "login"
                    st.rerun()

    if st.button("⬅ Volver al login"):
        st.session_state.pantalla = "login"
        st.rerun()
    st.stop()

# ================= APP PRINCIPAL =================
col1, col2 = st.columns([8, 1])
with col1:
    st.title("🧾 Sistema de Apoyo a la Auditoría de Pagos")
with col2:
    st.write("") 
    st.write("") 
    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ================= ENTRADA DE DATOS (CON FORMULARIO SEGURO) =================
with st.form("formulario_entrada", clear_on_submit=True):
    texto_pegado = st.text_area("📥 Pegue el texto aquí")
    cuenta_objetal_manual = st.text_input("🏷️ Cuenta Objetal (llenado manual por auditor)")
    
    enviado = st.form_submit_button("📤 Enviar al Historial")

    if enviado:
        if not texto_pegado.strip():
            st.warning("El campo de texto está vacío.")
        else:
            nuevo_registro = extraer_datos(texto_pegado)
            
            insert_reg_sql = """
                INSERT INTO registros (
                    institucion, estructura_programatica, numero_libramiento,
                    importe, clasificacion, rnc, cuenta_objetal, usuario_id
                )
                VALUES (:inst, :est, :lib, :imp, :clas, :rnc, :cta, :uid)
            """
            params_reg = {
                "inst": nuevo_registro["institucion"],
                "est": nuevo_registro["estructura_programatica"],
                "lib": nuevo_registro["numero_libramiento"],
                "imp": nuevo_registro["importe"],
                "clas": nuevo_registro["clasificacion"],
                "rnc": nuevo_registro["rnc"],
                "cta": cuenta_objetal_manual,
                "uid": st.session_state.usuario_id
            }
            
            if run_query(insert_reg_sql, params_reg):
                st.toast("✅ Registro guardado exitosamente")
                time.sleep(1)

# ================= HISTORIAL =================
st.markdown("---")
st.subheader("📊 Historial")

def colorear_estado(val):
    if val == "En proceso":
        return "background-color:#ffe5e5; color:red; font-weight:bold"
    elif val == "Completado":
        return "background-color:#e6ffe6; color:green; font-weight:bold"
    return ""

historial_sql = """
    SELECT id, institucion, numero_libramiento, estructura_programatica, 
           importe, cuenta_objetal, clasificacion, estado
    FROM registros
    WHERE usuario_id = :uid AND exportado = FALSE
    ORDER BY id DESC
"""
df_historial = get_data(historial_sql, params={"uid": st.session_state.usuario_id})

# --- INICIALIZAMOS VARIABLE ---
registro_sel = None 

if df_historial.empty:
    st.info("No hay expedientes registrados todavía.")
else:
    st.dataframe(
        df_historial.style.map(colorear_estado, subset=["estado"]),
        use_container_width=True
    )

    registro_sel = st.selectbox(
        "📌 Seleccione expediente",
        df_historial["id"],
        format_func=lambda x: f"#{x} — {df_historial.loc[df_historial.id==x,'institucion'].values[0]}"
    )
    
    if st.button("🗑️ Borrar expediente seleccionado"):
        del_sql = "DELETE FROM registros WHERE id = :id AND usuario_id = :uid"
        run_query(del_sql, params={"id": int(registro_sel), "uid": st.session_state.usuario_id})
        st.warning("Expediente eliminado")
        time.sleep(1)
        st.rerun()

# ================= VISTA PREVIA Y EDICIÓN (BLINDADA) =================
if registro_sel:
    datos_exp = df_historial[df_historial.id == registro_sel][[
        "institucion", "estructura_programatica", "numero_libramiento", 
        "importe", "cuenta_objetal", "clasificacion"
    ]]
    
    st.markdown("### 📄 Vista previa y Clasificación")
    
    # Configuramos el editor para cambiar la clasificación
    column_config = {
        "clasificacion": st.column_config.SelectboxColumn(
            "Clasificación",
            options=["General", "SERVICIOS BASICOS"], 
            width="medium",
            help="Si cambias a SERVICIOS BASICOS, aparecerá el formulario abajo."
        )
    }

    datos_editados = st.data_editor(
        datos_exp,
        column_config=column_config,
        disabled=["institucion","estructura_programatica","numero_libramiento","importe"], 
        use_container_width=True,
        key=f"preview_{registro_sel}"
    )
    
    # Detectamos cambios
    if not datos_editados.equals(datos_exp):
        nueva_cuenta = datos_editados.iloc[0]["cuenta_objetal"]
        nueva_clasif = datos_editados.iloc[0]["clasificacion"]
        
        upd_sql = "UPDATE registros SET cuenta_objetal = :cta, clasificacion = :clas WHERE id = :id AND usuario_id = :uid"
        params_upd = {
            "cta": nueva_cuenta, "clas": nueva_clasif, 
            "id": int(registro_sel), "uid": st.session_state.usuario_id
        }
        if run_query(upd_sql, params_upd):
            st.toast("✅ Clasificación actualizada. Recargando...")
            time.sleep(0.5)
            st.rerun()

    # LÓGICA PARA MOSTRAR EL FORMULARIO
    valor_actual_db = df_historial.loc[df_historial.id == registro_sel, "clasificacion"].values[0]
    clasif_limpia = str(valor_actual_db).strip().upper()

    # Si es SERVICIOS BASICOS, mostramos el formulario
    if "SERVICIOS BASICOS" in clasif_limpia:
        st.markdown("---")
        crear_formulario_bienes_servicios(registro_sel)
    else:
        # AVISO IMPORTANTE PARA EL USUARIO
        st.info("ℹ️ Este expediente es 'General'. Si necesitas llenar el formulario, cambia la Clasificación en la tabla de arriba a 'SERVICIOS BASICOS'.")

# ================= EXPORTACIÓN =================
st.markdown("---")
st.markdown("## 📤 Cerrar Lote y Exportar")

def marcar_como_archivados():
    update_sql = "UPDATE registros SET exportado = TRUE WHERE usuario_id = :uid AND exportado = FALSE"
    if run_query(update_sql, params={"uid": st.session_state.usuario_id}):
        st.toast("✅ Lote exportado y archivado correctamente.")

export_sql = """
    SELECT r.institucion, r.estructura_programatica, r.numero_libramiento, 
           r.importe, r.cuenta_objetal, r.clasificacion,
           f.CC, f.CP, f.OFI, f.FACT, f.FIRMA_DIGITAL, f.Recep,
           f.RPE, f.DGII, f.TSS, f.OC, f.CONT, f.TITULO,
           f.DETE, f.JURI_INMO, f.TASACION, f.APROB_PRESI, f.VIAJE_PRESI
    FROM registros r
    LEFT JOIN formulario_bienes_servicios f ON r.id = f.registro_id
    WHERE r.usuario_id = :uid AND r.exportado = FALSE
    ORDER BY r.id DESC
"""
df_export = get_data(export_sql, params={"uid": st.session_state.usuario_id})

if not df_export.empty:
    st.info(f"Tienes {len(df_export)} expedientes listos para exportar.")
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Auditoria")
    
    st.download_button(
        label="⬇️ Descargar Excel y Limpiar Pantalla",
        data=output.getvalue(),
        file_name="Auditoria_Lote.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        on_click=marcar_como_archivados
    )
else:
    st.write("No hay expedientes pendientes para exportar.")
