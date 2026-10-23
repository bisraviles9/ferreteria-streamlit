import json
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Ferretería | Inventario", page_icon="🔩", layout="wide")
ARCHIVO = Path(__file__).with_name("inventario_ferreteria.json")
PREFIJOS = {
    "Tornillería": "TOR",
    "Electricidad": "ELE",
    "Plomería": "PLO",
    "Herramientas": "HER",
    "Pintura": "PIN",
    "Construcción": "CON",
    "Seguridad": "SEG",
    "Otros": "OTR",
}


def cargar_datos():
    if ARCHIVO.exists():
        try:
            datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
            datos.setdefault("productos", [])
            datos.setdefault("ventas", [])
            return datos
        except (json.JSONDecodeError, OSError):
            st.error("No se pudo leer el inventario guardado. Se iniciará uno vacío.")
    return {"productos": [], "ventas": []}


def guardar_datos():
    ARCHIVO.write_text(
        json.dumps(st.session_state.datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generar_codigo(categoria):
    prefijo = PREFIJOS[categoria]
    codigos = [
        p["codigo"] for p in st.session_state.datos["productos"]
        if p["codigo"].startswith(f"FER-{prefijo}-")
    ]
    numeros = []
    for codigo in codigos:
        try:
            numeros.append(int(codigo.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    return f"FER-{prefijo}-{max(numeros, default=0) + 1:04d}"


if "datos" not in st.session_state:
    st.session_state.datos = cargar_datos()

datos = st.session_state.datos
productos = datos["productos"]

st.title("🔩 Gestión de ferretería")
st.caption("Inventario, códigos de producto, ventas y alertas de existencias. Los datos se guardan en inventario_ferreteria.json.")

# Resumen
col1, col2, col3, col4 = st.columns(4)
col1.metric("Productos", len(productos))
col2.metric("Unidades en stock", sum(p["stock"] for p in productos))
col3.metric("Valor del inventario", f"${sum(p['stock'] * p['precio_usd'] for p in productos):,.2f}")
col4.metric("Ventas acumuladas", f"${sum(v['total_usd'] for v in datos['ventas']):,.2f}")

pestanas = st.tabs(["Inventario", "Agregar producto", "Registrar venta", "Reponer stock", "Historial de ventas"])

with pestanas[0]:
    st.subheader("Productos")
    if productos:
        busqueda = st.text_input("Buscar por código, nombre o categoría", key="buscar").strip().lower()
        filtrados = [
            p for p in productos
            if busqueda in p["codigo"].lower()
            or busqueda in p["nombre"].lower()
            or busqueda in p["categoria"].lower()
        ]
        filas = [
            {
                "Código": p["codigo"],
                "Producto": p["nombre"],
                "Categoría": p["categoria"],
                "Precio (USD)": p["precio_usd"],
                "Stock": p["stock"],
                "Mínimo": p["stock_minimo"],
                "Estado": "⚠️ Reponer" if p["stock"] <= p["stock_minimo"] else "OK",
            }
            for p in filtrados
        ]
        st.dataframe(filas, use_container_width=True, hide_index=True)
        bajos = [p for p in productos if p["stock"] <= p["stock_minimo"]]
        if bajos:
            st.warning("Stock bajo: " + ", ".join(f"{p['nombre']} ({p['stock']})" for p in bajos))
    else:
        st.info("Aún no hay productos. Agrégalos desde la pestaña ‘Agregar producto’.")

with pestanas[1]:
    st.subheader("Agregar producto")
    with st.form("form_producto", clear_on_submit=True):
        nombre = st.text_input("Nombre del producto", placeholder="Ej.: Tornillo galvanizado 2 pulgadas")
        categoria = st.selectbox("Categoría", list(PREFIJOS))
        c1, c2, c3 = st.columns(3)
        precio = c1.number_input("Precio de venta (USD)", min_value=0.0, step=0.25, format="%.2f")
        stock = c2.number_input("Cantidad inicial", min_value=0, step=1)
        minimo = c3.number_input("Nivel mínimo de stock", min_value=0, step=1)
        guardar = st.form_submit_button("Guardar producto", type="primary")
        if guardar:
            if not nombre.strip():
                st.error("Escribe el nombre del producto.")
            else:
                codigo = generar_codigo(categoria)
                productos.append({
                    "codigo": codigo,
                    "nombre": nombre.strip(),
                    "categoria": categoria,
                    "precio_usd": round(precio, 2),
                    "stock": int(stock),
                    "stock_minimo": int(minimo),
                })
                guardar_datos()
                st.success(f"Producto guardado con el código {codigo}.")
                st.rerun()
    st.caption("Formato de código: FER-CATEGORÍA-0001. Ejemplo: FER-TOR-0001 para tornillería.")

with pestanas[2]:
    st.subheader("Registrar venta")
    disponibles = [p for p in productos if p["stock"] > 0]
    if disponibles:
        opciones = {f"{p['codigo']} — {p['nombre']} (stock: {p['stock']})": p for p in disponibles}
        with st.form("form_venta"):
            seleccionado = st.selectbox("Producto", list(opciones))
            p = opciones[seleccionado]
            cantidad = st.number_input("Unidades", min_value=1, max_value=p["stock"], step=1)
            st.write(f"Precio unitario: **${p['precio_usd']:.2f}** · Total: **${p['precio_usd'] * cantidad:.2f}**")
            vender = st.form_submit_button("Confirmar venta", type="primary")
            if vender:
                total = round(int(cantidad) * p["precio_usd"], 2)
                p["stock"] -= int(cantidad)
                datos["ventas"].append({
                    "codigo": p["codigo"], "producto": p["nombre"],
                    "cantidad": int(cantidad), "total_usd": total,
                })
                guardar_datos()
                st.success(f"Venta registrada: ${total:.2f}.")
                st.rerun()
    else:
        st.info("No hay productos con stock disponible.")

with pestanas[3]:
    st.subheader("Reponer stock")
    if productos:
        opciones = {f"{p['codigo']} — {p['nombre']} (stock: {p['stock']})": p for p in productos}
        with st.form("form_reponer"):
            seleccionado = st.selectbox("Producto", list(opciones))
            cantidad = st.number_input("Unidades que ingresan", min_value=1, step=1)
            reponer = st.form_submit_button("Actualizar stock", type="primary")
            if reponer:
                p = opciones[seleccionado]
                p["stock"] += int(cantidad)
                guardar_datos()
                st.success(f"Stock actualizado: {p['stock']} unidades.")
                st.rerun()
    else:
        st.info("Agrega productos primero para poder reponer existencias.")

with pestanas[4]:
    st.subheader("Historial de ventas")
    if datos["ventas"]:
        st.dataframe([
            {"Código": v["codigo"], "Producto": v["producto"], "Cantidad": v["cantidad"], "Total (USD)": v["total_usd"]}
            for v in reversed(datos["ventas"])
        ], use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay ventas registradas.")

st.divider()
st.caption("Códigos SKU internos para identificar productos; no reemplazan códigos de barras oficiales.")
