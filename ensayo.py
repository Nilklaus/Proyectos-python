import os
import streamlit as st
import pandas as pd

# ======================
# FUNCIONES
# ======================
def calcular_servicio_cuantia(cuantia, regla):
    umbral = regla["UMBRAL"]
    base = regla["TARIFA_BASE"]
    porcentaje = regla["PORCENTAJE_EXCEDENTE"]

    if cuantia <= umbral:
        return base
    else:
        return base + (cuantia - umbral) * porcentaje

# ======================
# CONFIGURACIÓN APP
# ======================
st.set_page_config(page_title="Factura Notarial", layout="centered")
st.title("🧾 Factura Notarial")

# ======================
# Ruta relativa desde carpeta de ejecución
archivo = "tarifas demo.xlsx"

# ======================
# Debug: mostrar carpeta actual y archivos
st.write("Directorio actual:", os.getcwd())
st.write("Archivos en la carpeta:", os.listdir())

# ======================
# Comprobar existencia del archivo
if not os.path.exists(archivo):
    st.error(f"No se encontró el archivo Excel en: {os.getcwd()}/{archivo}")
    st.stop()
else:
    st.success(f"Archivo encontrado: {archivo}")

# ======================
# TARIFAS FIJAS
df = pd.read_excel(archivo, sheet_name="Hoja de control", engine="openpyxl")
df = df.dropna(subset=["AÑO"])
df["AÑO"] = df["AÑO"].astype(int)

anios = sorted(df["AÑO"].unique(), reverse=True)
anio = st.selectbox("Seleccione el año", anios)

fila = df[df["AÑO"] == anio]
tarifas = fila.iloc[0].drop("AÑO").dropna().to_dict()

# ======================
# REGLAS POR CUANTÍA
reglas = pd.read_excel(archivo, sheet_name="Servicios por cuantia", engine="openpyxl")
reglas = reglas.dropna(subset=["SERVICIO"])

# ======================
# SESSION STATE
if "factura" not in st.session_state:
    st.session_state.factura = []

# ======================
# SERVICIOS POR CUANTÍA
st.subheader("➕ Servicio por cuantía")

servicios_cuantia = reglas[
    (reglas["AÑO_DESDE"] <= anio) & (reglas["AÑO_HASTA"] >= anio)
]["SERVICIO"].unique()

if len(servicios_cuantia) > 0:
    servicio_cuantia = st.selectbox("Servicio", servicios_cuantia)

    tipo_cmp = st.radio("Tipo de comparecientes", ["PARTICULARES", "PARTICULARES + EXENTOS"])

    cuantia = st.number_input("Cuantía del acto", min_value=0, step=1_000)

    if st.button("Agregar servicio por cuantía"):
        regla = reglas[
            (reglas["SERVICIO"] == servicio_cuantia) &
            (reglas["AÑO_DESDE"] <= anio) &
            (reglas["AÑO_HASTA"] >= anio)
        ].iloc[0]

        valor_calculado = calcular_servicio_cuantia(cuantia, regla)

        # Selección de tope
        tope = regla["TOPE_PARTICULARES"] if tipo_cmp == "PARTICULARES" else regla["TOPE_EXENTOS"]
        if pd.isna(tope):
            tope = None

        aporte_especial = 0
        if tope is not None and valor_calculado > tope:
            valor_servicio = tope
            aporte_especial = valor_calculado - tope
        else:
            valor_servicio = valor_calculado

        valor_servicio = int(round(valor_servicio))
        aporte_especial = int(round(aporte_especial))

        st.session_state.factura.append({
            "Servicio": servicio_cuantia,
            "Tipo": "Servicio por cuantía",
            "Cantidad": 1,
            "Valor unitario": valor_servicio,
            "IVA": True,
            "Editable": False,
            "Subtotal": valor_servicio
        })

        if aporte_especial > 0:
            st.session_state.factura.append({
                "Servicio": "Aporte especial",
                "Tipo": "Aporte especial",
                "Cantidad": 1,
                "Valor unitario": aporte_especial,
                "IVA": False,
                "Editable": False,
                "Subtotal": aporte_especial
            })

        st.success("Servicio agregado")

# ======================
# SERVICIOS DE TARIFA FIJA
st.subheader("➕ Servicio tarifa fija")

if tarifas:
    servicio = st.selectbox("Servicio", list(tarifas.keys()))
    cantidad = st.number_input("Cantidad", min_value=1, step=1)

    if st.button("Agregar servicio fijo"):
        valor = int(tarifas[servicio])
        st.session_state.factura.append({
            "Servicio": servicio,
            "Tipo": "Tarifa fija",
            "Cantidad": cantidad,
            "Valor unitario": valor,
            "IVA": True,
            "Editable": True,
            "Subtotal": cantidad * valor
        })
        st.success("Servicio agregado")

# ======================
# FACTURA
st.divider()
st.subheader("🧾 Factura")

if not st.session_state.factura:
    st.info("Aún no hay servicios agregados")
    st.stop()

total_gravado = 0
total_no_gravado = 0

for i, item in enumerate(st.session_state.factura):
    col1, col2, col3, col4, col5 = st.columns([4, 2, 2, 2, 1])

    with col1:
        st.write(item["Servicio"])
        st.caption(item["Tipo"])

    with col2:
        nueva = st.number_input("Cantidad", min_value=1, value=item["Cantidad"], step=1, key=f"cant_{i}")
        item["Cantidad"] = nueva

    with col3:
        st.write(f"${item['Valor unitario']:,.0f}")

    subtotal = item["Cantidad"] * item["Valor unitario"]
    item["Subtotal"] = subtotal

    with col4:
        st.write(f"${subtotal:,.0f}")

    with col5:
        if st.button("❌", key=f"del_{i}"):
            st.session_state.factura.pop(i)
            st.rerun()

    if item["IVA"]:
        total_gravado += subtotal
    else:
        total_no_gravado += subtotal

st.divider()

iva = int(round(total_gravado * 0.19))
total = total_gravado + total_no_gravado + iva

st.markdown(f"**Gravado:** ${total_gravado:,.0f}")
st.markdown(f"**No gravado:** ${total_no_gravado:,.0f}")
st.markdown(f"**IVA (19%):** ${iva:,.0f}")
st.markdown(f"## 💰 TOTAL: **${total:,.0f}**")