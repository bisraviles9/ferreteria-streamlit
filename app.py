import json
import re
import unicodedata
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Ferretería | Inventario", page_icon="🔩", layout="wide")
ARCHIVO = Path(__file__).with_name("inventario_ferreteria.json")
CATEGORIAS = [
    "Cemento y morteros", "Áridos (arena, grava, piedra)", "Bloques y ladrillos",
    "Acero, hierro y mallas", "Madera y tableros", "Cubiertas y techos",
    "Pinturas y recubrimientos", "Impermeabilización", "Adhesivos y selladores",
    "Pisos y revestimientos", "Puertas, ventanas y vidrio", "Plomería y sanitarios",
    "Electricidad e iluminación", "Herramientas manuales", "Herramientas eléctricas",
    "Tornillería y fijaciones", "Seguridad y protección", "Jardinería",
    "Equipos y maquinaria", "Transporte y almacenamiento", "Otros",
]
PREFIJOS = {
    "Cemento y morteros": "CEM", "Áridos (arena, grava, piedra)": "ARI",
    "Bloques y ladrillos": "BLO", "Acero, hierro y mallas": "ACE",
    "Madera y tableros": "MAD", "Cubiertas y techos": "TEC",
    "Pinturas y recubrimientos": "PIN", "Impermeabilización": "IMP",
    "Adhesivos y selladores": "ADH", "Pisos y revestimientos": "PIS",
    "Puertas, ventanas y vidrio": "PUE", "Plomería y sanitarios": "PLO",
    "Electricidad e iluminación": "ELE", "Herramientas manuales": "HMA",
    "Herramientas eléctricas": "HEE", "Tornillería y fijaciones": "TOR",
    "Seguridad y protección": "SEG", "Jardinería": "JAR",
    "Equipos y maquinaria": "EQU", "Transporte y almacenamiento": "TRA",
    "Otros": "OTR",
}
UNIDADES = [
    "unidad", "saco", "kg", "quintal", "tonelada", "g", "m", "cm", "m²", "m³",
    "litro", "galón", "ml", "caja", "paquete", "rollo", "plancha", "lámina",
    "barra", "varilla", "bloque", "ladrillo", "balde", "par", "juego",
]


def cargar_datos():
    if ARCHIVO.exists():
        try:
            datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
            datos.setdefault("productos", [])
            datos.setdefault("ventas", [])
            for p in datos["productos"]:
                p.setdefault("unidad", "unidad")
            return datos
        except (json.JSONDecodeError, OSError):
            st.error("No se pudo leer el inventario guardado. Se iniciará uno vacío.")
    return {"productos": [], "ventas": []}


def guardar_datos():
    ARCHIVO.write_text(json.dumps(st.session_state.datos, ensure_ascii=False, indent=2), encoding="utf-8")


def prefijo_categoria(categoria):
    if categoria in PREFIJOS:
        return PREFIJOS[categoria]
    normal = unicodedata.normalize("NFKD", categoria).encode("ascii", "ignore").decode("ascii")
    letras = re.sub(r"[^A-Za-z]", "", normal).upper()
    return (letras[:3] or "OTR").ljust(3, "X")


def generar_codigo(categoria):
    prefijo = prefijo_categoria(categoria)
    codigos = [p["codigo"] for p in st.session_state.datos["productos"] if p["codigo"].startswith(f"FER-{prefijo}-")]
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

st.title("🔩 Gestión de ferretería y materiales")
st.caption("Registra materiales de construcción y productos de ferretería por unidad, peso, longitud, área o volumen.")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Productos", len(productos))
col2.metric("Existencias", sum(p["stock"] for p in productos))
col3.metric("Valor del inventario", f"${sum(p['stock'] * p['precio_usd'] for p in productos):,.2f}")
col4.metric("Ventas acumuladas", f"${sum(v['total_usd'] for v in datos['ventas']):,.2f}")

pestanas = st.tabs(["Inventario", "Agregar producto", "Registrar venta", "Reponer stock", "Historial de ventas"])

with pestanas[0]:
    st.subheader("Catálogo e inventario")
    if productos:
        busqueda = st.text_input("Buscar por código, nombre o categoría", key="buscar").strip().lower()
        filtrados = [p for p in productos if busqueda in p["codigo"].lower() or busqueda in p["nombre"].lower() or busqueda in p["categoria"].lower()]
        st.dataframe([
            {"Código": p["codigo"], "Producto": p["nombre"], "Categoría": p["categoria"],
             "Precio (USD)": p["precio_usd"], "Unidad": p.get("unidad", "unidad"),
             "Stock": p["stock"], "Mínimo": p["stock_minimo"],
             "Estado": "⚠️ Reponer" if p["stock"] <= p["stock_minimo"] else "OK"}
            for p in filtrados
        ], use_container_width=True, hide_index=True)
        bajos = [p for p in productos if p["stock"] <= p["stock_minimo"]]
        if bajos:
            st.warning("Stock bajo: " + ", ".join(f"{p['nombre']} ({p['stock']} {p.get('unidad', 'unidad')})" for p in bajos))
    else:
        st.info("Aún no hay productos. Agrégalos desde la pestaña ‘Agregar producto’.")

with pestanas[1]:
    st.subheader("Agregar producto")
    with st.form("form_producto", clear_on_submit=True):
        nombre = st.text_input("Nombre o descripción", placeholder="Ej.: Cemento Portland, varilla corrugada 12 mm")
        categoria_sel = st.selectbox("Categoría", CATEGORIAS + ["➕ Otra categoría"])
        categoria = st.text_input("Escribe la categoría", placeholder="Ej.: Geotextiles, alquiler de equipos") if categoria_sel == "➕ Otra categoría" else categoria_sel
        c1, c2, c3 = st.columns(3)
        precio = c1.number_input("Precio por unidad (USD)", min_value=0.0, step=0.25, format="%.2f")
        unidad_sel = c2.selectbox("Unidad de venta", UNIDADES + ["Otra unidad"])
        unidad = c2.text_input("Escribe la unidad") if unidad_sel == "Otra unidad" else unidad_sel
        stock = c3.number_input("Existencias iniciales", min_value=0.0, step=1.0, format="%.2f")
        minimo = st.number_input("Avisarme cuando el stock llegue a", min_value=0.0, step=1.0, format="%.2f")
        guardar = st.form_submit_button("Guardar producto", type="primary")
        if guardar:
            if not nombre.strip() or not categoria.strip() or not unidad.strip():
                st.error("Completa el nombre, la categoría y la unidad.")
            else:
                codigo = generar_codigo(categoria.strip())
                productos.append({"codigo": codigo, "nombre": nombre.strip(), "categoria": categoria.strip(),
                                  "precio_usd": round(precio, 2), "unidad": unidad.strip(),
                                  "stock": float(stock), "stock_minimo": float(minimo)})
                guardar_datos()
                st.success(f"Producto guardado con el código {codigo}.")
                st.rerun()
    st.caption("Las categorías y unidades se pueden personalizar. El código SKU es interno y no reemplaza un código de barras oficial.")

with pestanas[2]:
    st.subheader("Registrar venta")
    disponibles = [p for p in productos if p["stock"] > 0]
    if disponibles:
        opciones = {f"{p['codigo']} — {p['nombre']} (stock: {p['stock']:g} {p.get('unidad', 'unidad')})": p for p in disponibles}
        with st.form("form_venta"):
            seleccionado = st.selectbox("Producto", list(opciones))
            p = opciones[seleccionado]
            cantidad = st.number_input("Cantidad", min_value=0.01, max_value=float(p["stock"]), step=1.0, format="%.2f")
            st.write(f"Precio por {p.get('unidad', 'unidad')}: **${p['precio_usd']:.2f}** · Total: **${p['precio_usd'] * cantidad:.2f}**")
            vender = st.form_submit_button("Confirmar venta", type="primary")
            if vender:
                total = round(float(cantidad) * p["precio_usd"], 2)
                p["stock"] = round(float(p["stock"]) - float(cantidad), 3)
                datos["ventas"].append({"codigo": p["codigo"], "producto": p["nombre"], "unidad": p.get("unidad", "unidad"), "cantidad": float(cantidad), "total_usd": total})
                guardar_datos()
                st.success(f"Venta registrada: ${total:.2f}.")
                st.rerun()
    else:
        st.info("No hay productos con existencias disponibles.")

with pestanas[3]:
    st.subheader("Reponer existencias")
    if productos:
        opciones = {f"{p['codigo']} — {p['nombre']} (stock: {p['stock']:g} {p.get('unidad', 'unidad')})": p for p in productos}
        with st.form("form_reponer"):
            seleccionado = st.selectbox("Producto", list(opciones))
            cantidad = st.number_input("Cantidad que ingresa", min_value=0.01, step=1.0, format="%.2f")
            reponer = st.form_submit_button("Actualizar stock", type="primary")
            if reponer:
                p = opciones[seleccionado]
                p["stock"] = round(float(p["stock"]) + float(cantidad), 3)
                guardar_datos()
                st.success(f"Stock actualizado: {p['stock']:g} {p.get('unidad', 'unidad')}.")
                st.rerun()
    else:
        st.info("Agrega productos primero para reponer existencias.")

with pestanas[4]:
    st.subheader("Historial de ventas")
    if datos["ventas"]:
        st.dataframe([{"Código": v["codigo"], "Producto": v["producto"], "Cantidad": f"{v['cantidad']:g} {v.get('unidad', 'unidad')}", "Total (USD)": v["total_usd"]} for v in reversed(datos["ventas"])], use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay ventas registradas.")

st.divider()
st.caption("Puedes registrar cualquier producto: las listas iniciales son sugerencias y admiten categorías y unidades personalizadas.")
