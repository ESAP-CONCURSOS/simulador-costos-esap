import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math

# ==============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Simulador de Costos",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# PALETA DE COLORES ESAP Y ESTILOS CSS
# ==============================================================================
ESAP_PALETTE = {
    "primary": "#003366",      # Azul institucional ESAP
    "secondary": "#004080",   # Azul secundario
    "accent": "#FF8C00",      # Naranja ESAP
    "orange": "#FFA500",      # Naranja claro
    "neutral_light": "#f8f9fa",
    "neutral_mid": "#6c757d",
    "neutral_dark": "#333333",
    "success": "#28a745",
    "warning": "#ffc107",
    "danger": "#dc3545",
}

# ==============================================================================
# FUNCIÓN REUTILIZABLE PARA HEADERS
# ==============================================================================
def render_header(titulo, emoji="📊"):
    """Renderiza el header principal de cada vista con estilo ESAP consistente."""
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #003366 0%, #004080 100%); 
                    padding: 2rem; 
                    border-radius: 12px; 
                    margin-bottom: 2rem;
                    box-shadow: 0 4px 12px rgba(0,51,102,0.2);
                    border-left: 6px solid #FF8C00;
                    animation: fadeIn 0.5s ease-in;">
            <h1 style="color: #ffffff !important; 
                       margin: 0; 
                       font-size: 2rem; 
                       font-weight: 700;
                       text-align: center;
                       text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
                       border: none;">
                <span style="color: #ffffff;">{emoji} {titulo}</span>
            </h1>
            <p style="color: #FFA500; 
                      text-align: center; 
                      margin: 0.5rem 0 0 0; 
                      font-size: 1rem;">
                Escuela Superior de Administración Pública
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


# Metadatos de los módulos para el tablero de inicio.
# 'pf' = llave en pf_store (None para la vista ejecutiva). 'avance' se ajustará luego.
INICIO_MODULOS = [
    {"nombre": "Logística", "icono": "🚚", "estado": "Finalizado", "avance": 100, "pf": "Logística"},
    {"nombre": "VRM-VA", "icono": "🧪", "estado": "Finalizado", "avance": 100, "pf": "VRM-VA"},
    {"nombre": "Jurídico", "icono": "⚖️", "estado": "Finalizado", "avance": 100, "pf": "Jurídico"},
    {"nombre": "Construcción y Calificación", "icono": "🏗️📝", "estado": "Finalizado", "avance": 100, "pf": "Construcción y Calificación"},
    {"nombre": "Proyección Financiera", "icono": "💰", "estado": "Finalizado", "avance": 100, "pf": None},
]
ESTADO_COLOR = {"Finalizado": "#1a7f37", "En validación": "#FF8C00", "Vista ejecutiva": "#0066CC"}


def _rango_texto(vmin, vmax):
    # Usa etiquetas Mín/Máx (no un guion) para no confundir con una resta.
    if abs(vmax - vmin) > 0.5:
        return f"Mín ${vmin:,.0f} · Máx ${vmax:,.0f}"
    return f"${vmax:,.0f}"


def render_inicio_proyecto():
    render_header("Vista General del Proyecto", "🏛️")
    _init_pf_store()
    store = st.session_state.get("pf_store", {})

    st.markdown(
        """
        <div class="custom-card">
            <p style="margin: 0; color: #333;">
                <strong>Simulador de Costos ESAP</strong> — estima y consolida los costos de las etapas de un
                concurso de méritos. Cada módulo calcula sus costos y aquí ves el <strong>consolidado del proyecto</strong>
                en tiempo real.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    modulos_directos = [m for m in INICIO_MODULOS if m["pf"]]
    total_min = sum(store.get(m["pf"], {}).get("min", 0) for m in modulos_directos)
    total_max = sum(store.get(m["pf"], {}).get("max", 0) for m in modulos_directos)
    valor_min = total_min * (1 + CARGA_ADMIN_TOTAL)
    valor_max = total_max * (1 + CARGA_ADMIN_TOTAL)
    hay_datos = total_max > 0
    n_con_datos = sum(1 for m in modulos_directos if store.get(m["pf"], {}).get("max", 0) > 0)

    # -------------------- 1. Resumen financiero en vivo --------------------
    st.subheader("💵 Resumen financiero del proyecto")
    if not hay_datos:
        st.info("Aún no hay costos calculados en esta sesión. Entra a cada módulo, presiona **Calcular** "
                "y el consolidado aparecerá aquí automáticamente.")
    else:
        rango = abs(total_max - total_min) > 0.5
        st.markdown("**Costo directo total**")
        if rango:
            cc1, cc2 = st.columns(2)
            cc1.metric("Mínimo", f"${total_min:,.0f}")
            cc2.metric("Máximo", f"${total_max:,.0f}")
        else:
            st.metric("Total", f"${total_max:,.0f}")
        st.markdown("**Valor total del proyecto**")
        if rango:
            vv1, vv2 = st.columns(2)
            vv1.metric("Mínimo", f"${valor_min:,.0f}")
            vv2.metric("Máximo", f"${valor_max:,.0f}")
        else:
            st.metric("Total", f"${valor_max:,.0f}")
        st.caption("Valor total = costos directos × 1.3505 (carga administrativa 35.05%). "
                   "Detalle en el módulo Proyección Financiera.")

        # -------------------- 2. Gráfico de composición --------------------
        comp = [(m["icono"] + " " + m["nombre"], store.get(m["pf"], {}).get("max", 0)) for m in modulos_directos]
        comp = [(n, v) for n, v in comp if v > 0]
        if comp:
            df_comp = pd.DataFrame(comp, columns=["Módulo", "Costo"]).sort_values("Costo")
            fig = px.bar(df_comp, x="Costo", y="Módulo", orientation="h",
                         text=df_comp["Costo"].map(lambda v: f"${v:,.0f}"),
                         color="Módulo", color_discrete_sequence=px.colors.sequential.Blues_r)
            fig.update_layout(showlegend=False, height=260, margin=dict(l=0, r=0, t=30, b=0),
                              title="Composición del costo directo (máximo)", xaxis_title=None, yaxis_title=None)
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

    # -------------------- 4/5. Captura y avance global --------------------
    colp1, colp2 = st.columns(2)
    with colp1:
        st.caption("Estado de captura de datos (sesión actual)")
        st.progress(n_con_datos / len(modulos_directos),
                    text=f"{n_con_datos} de {len(modulos_directos)} módulos con datos")
    with colp2:
        avance_global = sum(m["avance"] for m in INICIO_MODULOS) / len(INICIO_MODULOS)
        st.caption("Avance del proyecto · finalizado")
        st.progress(avance_global / 100, text=f"Avance global: {avance_global:.0f}%")

    # -------------------- 3. Tarjetas de módulo --------------------
    st.subheader("🧭 Módulos")
    for fila_inicio in range(0, len(INICIO_MODULOS), 3):
        fila = INICIO_MODULOS[fila_inicio:fila_inicio + 3]
        cols = st.columns(3)
        for col, m in zip(cols, fila):
            with col:
                with st.container(border=True):
                    color = ESTADO_COLOR.get(m["estado"], "#666")
                    st.markdown(
                        f"<div style='font-size:1.6rem'>{m['icono']}</div>"
                        f"<div style='font-weight:700;font-size:0.95rem;line-height:1.1'>{m['nombre']}</div>"
                        f"<span style='background:{color};color:#fff;border-radius:6px;padding:1px 8px;"
                        f"font-size:0.72rem'>{m['estado']}</span>",
                        unsafe_allow_html=True,
                    )
                    st.progress(m["avance"] / 100)
                    if m["pf"]:
                        vals = store.get(m["pf"], {})
                        if vals.get("max", 0) > 0:
                            st.markdown(f"**{_rango_texto(vals.get('min', 0), vals.get('max', 0))}**")
                        else:
                            st.caption("Sin datos aún")
                    else:
                        if hay_datos:
                            st.markdown(f"**{_rango_texto(valor_min, valor_max)}**")
                        else:
                            st.caption("Consolida los módulos")

    with st.expander("🧩 Cómo funciona / flujo recomendado"):
        st.markdown(
            """
            **Flujo sugerido:** 🚚 Logística → 🧪 VRM-VA → ⚖️ Jurídico → 🏗️📝 Construcción y Calificación → 💰 Proyección Financiera.

            - Cada módulo calcula sus costos con su propia lógica de negocio.
            - Los totales se acumulan durante la sesión y se consolidan en **Proyección Financiera**,
              que aplica la carga administrativa (35.05%) y calcula el valor total del proyecto.
            - Los valores se conservan al navegar entre módulos y solo se reinician con los botones **Borrar**.
            """
        )


def render_vrm_va_construccion():
    render_header("Módulo VRM-VA", "🧪")

    _init_pf_store()
    if "vrm_result" not in st.session_state:
        st.session_state.vrm_result = None
    if "va_result" not in st.session_state:
        st.session_state.va_result = None
    if "vrm_ingresos_total" not in st.session_state:
        st.session_state.vrm_ingresos_total = 0
    if "va_ingresos_total" not in st.session_state:
        st.session_state.va_ingresos_total = 0

    # Equipo base al inicio del módulo; su costo se suma al total de VRM-VA.
    costo_equipo_vrmva = render_equipo_base("vrmva")

    st.markdown("### Flujo de trabajo VRM")

    niveles_jerarquicos = [
        "Asistencial",
        "Tecnico",
        "Profesional Universitario",
        "Profesional Especializado",
        "Asesor",
        "Directivo",
        "Mixto",
        "Docentes",
    ]

    concursos_va = [
        "Otro",
        "Municipios 5ta y 6ta",
        "Municipios Priorizados",
        "Comisionado CNSC",
        "Directores Territoriales",
        "Personeros Municipales",
        "Docentes ESAP",
    ]

    metodologia = st.selectbox(
        "Metodologia",
        ["CNSC", "ESAP Tradicional", "ESAP Doble Ciego"],
        index=0,
        key="vrm_metodologia",
    )

    reglas_meta_vrm = {
        "Asistencial": {"meta_base": 55.0, "items_tipicos": 3, "variacion_por_item": 10.0},
        "Tecnico": {"meta_base": 40.0, "items_tipicos": 3, "variacion_por_item": 5.0},
        "Profesional Universitario": {"meta_base": 30.0, "items_tipicos": 3, "variacion_por_item": 4.0},
        "Profesional Especializado": {"meta_base": 25.0, "items_tipicos": 4, "variacion_por_item": 4.0},
        "Asesor": {"meta_base": 20.0, "items_tipicos": 4, "variacion_por_item": 2.0},
        "Directivo": {"meta_base": 20.0, "items_tipicos": 4, "variacion_por_item": 2.0},
        "Mixto": {"meta_base": 30.0, "items_tipicos": 3, "variacion_por_item": 4.0},
        "Docentes": {"meta_base": 8.0, "items_tipicos": 5, "variacion_por_item": 1.0},
    }

    # Valores compartidos entre módulos (autollenado editable).
    inscritos_def = int(st.session_state.get("global_inscritos", 1000)) or 1000
    dias_vrm_def = int(st.session_state.get("global_dias_vrm", 20)) or 20
    if st.session_state.get("global_inscritos"):
        st.caption(f"🔗 Inscritos autollenados desde otro módulo: {inscritos_def:,.0f} (editable).")

    with st.form("form_vrm"):
        col1, col2 = st.columns(2)

        with col1:
            dias_habiles = st.number_input(
                "Dias habiles VRM",
                min_value=1,
                value=dias_vrm_def,
                step=1,
            )

            inscritos = st.number_input(
                "Numero de inscritos",
                min_value=1,
                value=inscritos_def,
                step=1,
            )

        with col2:
            nivel_jerarquico = st.selectbox(
                "Nivel jerarquico",
                niveles_jerarquicos,
                index=2,
            )

            if metodologia != "CNSC":
                numero_items = st.number_input(
                    "Numero de items a calificar",
                    min_value=1,
                    value=3,
                    step=1,
                )
            else:
                st.markdown("*(En CNSC se conserva el nivel jerárquico, pero no se usan items para la meta diaria)*")
                numero_items = None

        calcular = st.form_submit_button("Calcular personal VRM")

    if calcular:
        # La meta diaria VRM es fija (30) en CNSC o nivel Mixto; si no, se ajusta por ítems.
        meta_fija = (metodologia == "CNSC") or (nivel_jerarquico == "Mixto")
        if meta_fija:
            meta_base = 30.0
            items_tipicos = None
            variacion_por_item = None
            meta_diaria = 30.0
        else:
            regla_nivel = reglas_meta_vrm[nivel_jerarquico]
            meta_base = regla_nivel["meta_base"]
            items_tipicos = regla_nivel["items_tipicos"]
            variacion_por_item = regla_nivel["variacion_por_item"]
            meta_diaria = meta_base - ((numero_items - items_tipicos) * variacion_por_item)

        meta_diaria = max(meta_diaria, 1.0)

        # Personal: ROUNDUP((factor * inscritos / dias / meta) * 1.1). El +10% aplica
        # a todas las metodologías; Doble Ciego duplica la base (factor 2).
        factor_dc = 2 if metodologia == "ESAP Doble Ciego" else 1
        analistas_totales = math.ceil((factor_dc * inscritos / dias_habiles / meta_diaria) * 1.10)
        auditores = math.ceil(analistas_totales / 2)
        supervisores = auditores if metodologia == "CNSC" else 0
        profesionales_apoyo = 3 if metodologia == "CNSC" else 0
        coordinadores = 1

        if metodologia == "CNSC":
            nota_metodologia = "CNSC: meta fija de 30 carpetas/día, +10% de personal y estructura de soporte (supervisores, 3 profesionales de apoyo, 1 coordinador)."
        elif metodologia == "ESAP Tradicional":
            nota_metodologia = "ESAP Tradicional: meta ajustada por ítems e incorpora un margen del 10% de personal."
        else:
            nota_metodologia = "ESAP Doble Ciego: duplica la base y añade un margen del 10% de personal."

        parametros_dict = {
            "Parametro": [
                "Metodologia",
                "Dias habiles",
                "Numero de inscritos",
            ],
            "Valor": [
                metodologia,
                f"{dias_habiles:,.0f}",
                f"{inscritos:,.0f}",
            ],
        }

        if not meta_fija:
            parametros_dict["Parametro"].extend([
                "Nivel jerarquico",
                "Meta base diaria",
                "Items tipicos",
                "Variacion por item",
                "Numero de items",
            ])
            parametros_dict["Valor"].extend([
                nivel_jerarquico,
                f"{meta_base:.2f} carpetas/dia",
                f"{items_tipicos:,.0f}",
                f"{variacion_por_item:.2f}",
                f"{numero_items:,.0f}",
            ])
        else:
            origen_fija = "CNSC" if metodologia == "CNSC" else "Mixto"
            parametros_dict["Parametro"].extend(["Nivel jerarquico", f"Meta fija ({origen_fija})"])
            parametros_dict["Valor"].extend([nivel_jerarquico, "30.00 carpetas/dia"])

        parametros_dict["Parametro"].append("Meta diaria por analista")
        parametros_dict["Valor"].append(f"{meta_diaria:.2f} carpetas/dia")

        cuadro_personal = [
            {"Rol": "Analistas totales", "Cantidad": analistas_totales},
            {"Rol": "Auditores", "Cantidad": auditores},
            {"Rol": "Supervisores", "Cantidad": supervisores},
            {"Rol": "Profesionales de apoyo", "Cantidad": profesionales_apoyo},
            {"Rol": "Coordinadores", "Cantidad": coordinadores},
        ]

        st.session_state.vrm_result = {
            "parametros": pd.DataFrame(parametros_dict),
            "personal": pd.DataFrame(cuadro_personal),
            "nota": nota_metodologia,
        }
        st.session_state.vrm_inputs = {
            "inscritos": inscritos,
            "dias_habiles": dias_habiles,
            "metodologia": metodologia,
        }
        # Valores compartidos entre módulos (autollenado editable).
        st.session_state["global_inscritos"] = inscritos
        st.session_state["global_dias_vrm"] = dias_habiles
        st.session_state["global_nivel_vrm"] = nivel_jerarquico

    if st.session_state.vrm_result is None:
        st.info("Completa los datos y presiona 'Calcular personal VRM'.")
    else:
        st.markdown("### Formato de salida")
        st.dataframe(st.session_state.vrm_result["parametros"], use_container_width=True, hide_index=True)
        st.dataframe(st.session_state.vrm_result["personal"], use_container_width=True, hide_index=True)
        if "vrm_ded_coord" not in st.session_state:
            st.session_state["vrm_ded_coord"] = 100
        ded_coord_vrm = st.number_input(
            "Dedicación del coordinador (%)", min_value=0, max_value=100, step=5,
            key="vrm_ded_coord", help="Afecta el costo del coordinador en esta etapa.",
        )
        personal_vrm = _con_dedicacion_coordinador(st.session_state.vrm_result["personal"], ded_coord_vrm)
        render_ingresos_manual_por_roles(
            personal_vrm,
            prefijo="vrm",
            dias_requeridos=st.session_state.vrm_inputs["dias_habiles"],
            titulo="Costo total etapa VRM",
        )
        st.session_state.vrm_ingresos_total = st.session_state.get("vrm_ingresos_total", 0)

    # -------------------- BLOQUE VA --------------------
    st.markdown("### Flujo de trabajo VA")

    with st.form("form_va"):
        c1, c2 = st.columns(2)

        with c1:
            dias_habiles_va = st.number_input(
                "Dias habiles VA",
                min_value=1,
                value=10,
                step=1,
                key="dias_habiles_va",
            )

            va_antes_pruebas = st.radio(
                "VA antes de pruebas",
                ["SI", "NO"],
                index=0,
                horizontal=True,
                key="va_antes_pruebas",
            )

        with c2:
            concurso = st.selectbox(
                "Concurso",
                concursos_va,
                index=0,
                key="concurso_va",
            )

            nivel_jerarquico_va = nivel_jerarquico
            st.caption(f"Nivel usado desde VRM: {nivel_jerarquico_va}")
            if concurso == "Otro":
                st.caption("Concurso 'Otro': la tasa de conversión se toma por nivel jerárquico.")
            else:
                st.caption("La tasa de conversión se toma por convocatoria (no depende del nivel).")

        calcular_va = st.form_submit_button("Calcular personal VA")

    if calcular_va:
        inscritos_base_va = st.session_state.get("vrm_inputs", {}).get("inscritos", None)
        if inscritos_base_va is None:
            st.error("Primero calcula VRM para reutilizar el número de inscritos base.")
            return

        configuracion_va = obtener_configuracion_va(concurso, nivel_jerarquico_va, va_antes_pruebas, metodologia)
        tasa_conversion_va = configuracion_va["tasa"]
        columna_tasa_va = configuracion_va["columna_tasa"]
        meta_diaria_va = configuracion_va["meta_diaria"]
        origen_meta_va = configuracion_va["origen_meta"]
        origen_tasa_va = configuracion_va["origen_tasa"]

        # Volumen VA = ROUNDUP(inscritos * tasa). La diferencia por nivel ya está
        # incorporada en la tasa de conversión, así que no se aplica ningún factor extra.
        volumen_va = math.ceil(inscritos_base_va * tasa_conversion_va)
        st.session_state.va_volumen = volumen_va
        st.session_state["global_dias_va"] = dias_habiles_va

        capacidad_individual_va = meta_diaria_va * dias_habiles_va

        # Mismo esquema de personal que VRM: +10% siempre, factor 2 en Doble Ciego.
        factor_dc = 2 if metodologia == "ESAP Doble Ciego" else 1
        analistas_totales_va = math.ceil((factor_dc * volumen_va / dias_habiles_va / meta_diaria_va) * 1.10)
        auditores_va = math.ceil(analistas_totales_va / 2)
        supervisores_va = auditores_va if metodologia == "CNSC" else 0
        profesionales_apoyo_va = 3 if metodologia == "CNSC" else 0
        coordinadores_va = 1

        parametros_dict_va = {
            "Parametro": [
                "Concurso",
                "VA antes de pruebas",
                "Dias habiles VA",
                "Numero de inscritos base VRM",
                "Fuente de tasa",
                "Columna tasa aplicada",
                "Nivel jerarquico VRM",
                "Tasa de conversion dinamica",
                "Volumen de trabajo VA",
                "Meta diaria VA",
                "Fuente meta diaria",
                "Capacidad individual",
            ],
            "Valor": [
                concurso,
                va_antes_pruebas,
                f"{dias_habiles_va:,.0f}",
                f"{inscritos_base_va:,.0f}",
                origen_tasa_va,
                columna_tasa_va,
                nivel_jerarquico,
                f"{tasa_conversion_va:.4f}",
                f"{volumen_va:,.0f}",
                f"{meta_diaria_va:.2f}",
                origen_meta_va,
                f"{capacidad_individual_va:,.0f}",
            ],
        }

        cuadro_personal_va = [
            {"Rol": "Analistas totales", "Cantidad": analistas_totales_va},
            {"Rol": "Auditores", "Cantidad": auditores_va},
            {"Rol": "Supervisores", "Cantidad": supervisores_va},
            {"Rol": "Profesionales de apoyo", "Cantidad": profesionales_apoyo_va},
            {"Rol": "Coordinadores", "Cantidad": coordinadores_va},
        ]

        st.session_state.va_result = {
            "parametros": pd.DataFrame(parametros_dict_va),
            "personal": pd.DataFrame(cuadro_personal_va),
        }

    if st.session_state.va_result is None:
        st.info("Completa los datos y presiona 'Calcular personal VA'.")
    else:
        st.markdown("### Formato de salida")
        st.dataframe(st.session_state.va_result["parametros"], use_container_width=True, hide_index=True)
        st.dataframe(st.session_state.va_result["personal"], use_container_width=True, hide_index=True)
        if "va_ded_coord" not in st.session_state:
            st.session_state["va_ded_coord"] = 100
        ded_coord_va = st.number_input(
            "Dedicación del coordinador (%)", min_value=0, max_value=100, step=5,
            key="va_ded_coord", help="Afecta el costo del coordinador en esta etapa.",
        )
        personal_va = _con_dedicacion_coordinador(st.session_state.va_result["personal"], ded_coord_va)
        render_ingresos_manual_por_roles(
            personal_va,
            prefijo="va",
            dias_requeridos=dias_habiles_va,
            titulo="Costo total etapa VA",
        )
        st.session_state.va_ingresos_total = st.session_state.get("va_ingresos_total", 0)

    total_vrm_va = (st.session_state.get("vrm_ingresos_total", 0)
                    + st.session_state.get("va_ingresos_total", 0)
                    + costo_equipo_vrmva)
    pf_registrar("VRM-VA", total_vrm_va)
    st.divider()
    st.markdown("### Costo Total VRM y VA")
    st.metric("Costo total del módulo", f"${total_vrm_va:,.0f}")
    render_boton_borrar_modulo(
        "VRM-VA",
        ["vrm_result", "va_result", "vrm_inputs", "vrm_ingresos_total",
         "va_ingresos_total", "va_volumen", "vrmva_equipo_df", "vrmva_equipo_editor"],
    )


def render_modulo_en_construccion(nombre_modulo, estado="Próximamente"):
    render_header(nombre_modulo, "🧱")

    st.markdown(
        f"""
        <div class="custom-card">
            <p style="margin: 0; color: #333; font-size: 1.05rem;">
                <strong>{estado}</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown(
    f"""
    <style>
        :root {{
            --esap-primary: {ESAP_PALETTE['primary']};
            --esap-secondary: {ESAP_PALETTE['secondary']};
            --esap-accent: {ESAP_PALETTE['accent']};
            --esap-orange: {ESAP_PALETTE['orange']};
        }}
        
        .stApp {{
            background: linear-gradient(180deg, rgba(0,51,102,0.05) 0%, rgba(255,140,0,0.02) 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #003366 0%, #004080 50%, #003366 100%);
            border-right: 3px solid var(--esap-accent);
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        }}
        
        section[data-testid="stSidebar"] * {{
            color: #ffffff !important;
        }}
        
        section[data-testid="stSidebar"] .stRadio label {{
            font-weight: 600;
            font-size: 0.95rem;
        }}
        
        section[data-testid="stSidebar"] .stRadio > div {{
            background: rgba(255,255,255,0.1);
            padding: 0.5rem;
            border-radius: 8px;
        }}
        
        /* Métricas */
        .stMetric {{
            background: rgba(255,255,255,0.95);
            padding: 1.2rem;
            border-radius: 12px;
            border-left: 4px solid var(--esap-accent);
            box-shadow: 0 4px 12px rgba(0,51,102,0.1);
            transition: transform 0.2s ease;
        }}
        
        .stMetric:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,51,102,0.15);
        }}
        
        div[data-testid="stMetricValue"] {{
            color: var(--esap-primary) !important;
            font-weight: 700;
            font-size: 2rem;
        }}
        
        div[data-testid="stMetricLabel"] {{
            color: var(--esap-neutral-mid) !important;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.05em;
        }}
        
        /* Botones */
        .stButton button {{
            background: linear-gradient(135deg, var(--esap-accent), var(--esap-orange));
            color: #ffffff !important;
            font-weight: 700;
            border-radius: 8px;
            border: none;
            padding: 0.7rem 2rem;
            box-shadow: 0 4px 8px rgba(255,140,0,0.3);
            transition: all 0.3s ease;
        }}
        
        .stButton button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(255,140,0,0.4);
        }}
        
        /* Títulos */
        h1 {{
            color: #000000 !important;
            font-weight: 700;
            border-bottom: 3px solid var(--esap-accent);
            padding-bottom: 0.5rem;
            margin-bottom: 1.5rem;
        }}
        
        h2 {{
            color: #000000 !important;
            font-weight: 600;
        }}
        
        h3 {{
            color: #000000 !important;
            font-weight: 600;
        }}
        
        /* DataFrames y Tablas */
        .stDataFrame {{
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,51,102,0.08);
            border: 1px solid rgba(0,51,102,0.1);
        }}
        
        /* Columnas */
        div[data-testid="column"] {{
            background: rgba(255,255,255,0.5);
            padding: 1rem;
            border-radius: 8px;
        }}
        
        /* Notificaciones */
        div[data-testid="stNotification"] {{
            border-left: 4px solid var(--esap-accent);
        }}
        
        /* Expanders */
        .streamlit-expanderHeader {{
            background: rgba(0,51,102,0.05);
            border-left: 3px solid var(--esap-accent);
            font-weight: 600;
        }}
        
        /* Animaciones */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateX(-20px); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}
        
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.02); }}
            100% {{ transform: scale(1); }}
        }}
        
        /* Responsive - Móvil */
        @media (max-width: 768px) {{
            .stMetric {{
                padding: 0.8rem;
                margin-bottom: 0.5rem;
            }}
            
            h1 {{
                font-size: 1.5rem !important;
            }}
            
            div[data-testid="stMetricValue"] {{
                font-size: 1.5rem;
            }}
            
            section[data-testid="stSidebar"] {{
                min-width: 200px;
            }}
        }}
        
        /* Cards personalizadas */
        .custom-card {{
            background: rgba(255,255,255,0.95);
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,51,102,0.1);
            border-left: 4px solid var(--esap-accent);
            margin-bottom: 1rem;
            animation: slideIn 0.3s ease-out;
        }}
        
        .summary-badge {{
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin: 0.2rem;
        }}
        
        .badge-success {{
            background: rgba(40, 167, 69, 0.15);
            color: #28a745;
        }}
        
        .badge-warning {{
            background: rgba(255, 193, 7, 0.15);
            color: #856404;
        }}
        
        .badge-info {{
            background: rgba(0, 123, 255, 0.15);
            color: #004085;
        }}
        
        /* ========== ESTILOS MEJORADOS PARA PESTAÑAS ========== */
        /* Contenedor de pestañas */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background: linear-gradient(135deg, rgba(0,51,102,0.08) 0%, rgba(255,140,0,0.05) 100%);
            padding: 12px 16px;
            border-radius: 16px 16px 0 0;
            border-bottom: 3px solid var(--esap-accent);
            margin-bottom: 0;
        }}
        
        /* Botones de pestañas individuales */
        .stTabs [data-baseweb="tab"] {{
            height: auto;
            padding: 14px 24px;
            background: rgba(255,255,255,0.9);
            border-radius: 12px 12px 0 0;
            border: 2px solid transparent;
            border-bottom: none;
            font-weight: 600;
            font-size: 0.95rem;
            color: var(--esap-primary);
            transition: all 0.3s ease;
            box-shadow: 0 -2px 8px rgba(0,51,102,0.1);
            margin-bottom: -3px;
        }}
        
        /* Hover en pestañas */
        .stTabs [data-baseweb="tab"]:hover {{
            background: rgba(255,140,0,0.15);
            border-color: var(--esap-accent);
            transform: translateY(-2px);
            color: var(--esap-primary);
        }}
        
        /* Pestaña activa/seleccionada */
        .stTabs [aria-selected="true"] {{
            background: linear-gradient(135deg, var(--esap-primary) 0%, var(--esap-secondary) 100%) !important;
            color: #ffffff !important;
            border-color: var(--esap-primary) !important;
            box-shadow: 0 -4px 12px rgba(0,51,102,0.25) !important;
            transform: translateY(-3px);
        }}
        
        /* Contenido de las pestañas */
        .stTabs [data-baseweb="tab-panel"] {{
            background: rgba(255,255,255,0.95);
            padding: 24px;
            border-radius: 0 0 16px 16px;
            border: 2px solid rgba(0,51,102,0.1);
            border-top: none;
            box-shadow: 0 4px 12px rgba(0,51,102,0.08);
        }}
        
        /* Indicador visual de navegación */
        .tab-navigation-hint {{
            background: linear-gradient(90deg, rgba(255,140,0,0.1) 0%, rgba(0,51,102,0.1) 100%);
            padding: 10px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            border-left: 4px solid var(--esap-accent);
            font-size: 0.9rem;
            color: var(--esap-primary);
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# DATOS MAESTROS (CONSTANTES)
# ==============================================================================
# BASE DE DATOS: 'Ciudad': [(Limite_R1, Precio_R1), (Limite_R2, Precio_R2), (Limite_R3, Precio_R3)]
TARIFARIO_DINAMICO = {
    'Medellín':     [(60, 122241), (80, 41738), (90, 38622)],
    'Arauca':       [(60, 84067), (150, 67159), (200, 70195)],
    'Barranquilla': [(30, 75192), (40, 256818), (60, 59254)],
    'Cartagena':    [(40, 72733), (60, 63442), (80, 56277)],
    'Tunja':        [(60, 125619), (80, 29874), (100, 28069)],
    'Manizales':    [(20, 255402), (30, 342424), (40, 128070)],
    'Florencia':    [(10, 1390909), (15, 927273), (35, 76983)],
    'Yopal':        [(50, 157850), (70, 198701), (90, 61669)],
    'Popayán':      [(20, 241250), (40, 256818), (60, 95316)],
    'Valledupar':   [(20, 235340), (40, 302273), (60, 71270)],
    'Quibdó':       [(50, 85180), (70, 198701), (90, 61382)],
    'Montería':     [(10, 1209091), (20, 604545), (30, 87049)],
    'Neiva':        [(50, 51194), (70, 45833), (80, 42051)],
    'Riohacha':     [(10, 1390909), (15, 927273), (35, 110447)],
    'Santa Marta':  [(30, 201855), (50, 241818), (60, 83287)],
    'Villavicencio':[(30, 189811), (40, 302273), (40, 118593)],
    'Pasto':        [(40, 81041), (60, 69076), (70, 61654)],
    'Bogotá':       [(120, 83729), (150, 62275), (200, 47055)],
    'Cúcuta':       [(20, 240305), (40, 302273), (60, 76463)],
    'Mocoa':        [(10, 1390909), (20, 695455), (30, 114434)],
    'Armenia':      [(50, 52251), (70, 47151), (90, 42993)],
    'Pereira':      [(60, 50643), (80, 45330), (100, 41300)],
    'San Andrés':   [(10, 1572727), (10, 1572727), (20, 138563)],
    'Bucaramanga':  [(40, 165536), (60, 201515), (80, 82801)],
    'Sincelejo':    [(20, 250082), (20, 604545), (40, 87534)],
    'Ibagué':       [(60, 129655), (80, 31983), (100, 30041)],
    'Cali':         [(20, 190582), (40, 104349), (60, 72246)]
}

# Claves exactas usadas en el bloque financiero consolidado.
# Mantenerlas alineadas evita errores en resúmenes, gráficos y exportables.
KEYS_MATERIALES = [
    'Infraestructura (Diagramación)', 'Material Examen Aplicación', 'Material Examen Exhibición',
    'Lectura y Procesamiento', 'Material Aplicación (Papelería)', 'Kit de Aplicación',
    'Kit Dactiloscopista', 'Empaque', 'Disposición Final'
]

# Lista ordenada de ciudades disponibles (evita duplicación)
CIUDADES_DISPONIBLES = sorted([
    'Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'San Andrés', 'Quibdó', 
    'Ibagué', 'Tunja', 'Villavicencio', 'Pereira', 'Manizales', 'Cartagena', 
    'Santa Marta', 'Riohacha', 'Arauca', 'Cúcuta', 'Pasto', 'Popayán',
    'Florencia', 'Yopal', 'Valledupar', 'Montería', 'Neiva', 'Mocoa',
    'Armenia', 'Bucaramanga', 'Sincelejo'
])

# Tablas internas del módulo VA.
# No dependen de una base externa; sirven como fuente local para tasas y metas.
NIVELES_JERARQUICOS = [
    'Asistencial',
    'Tecnico',
    'Profesional Universitario',
    'Especializado',
    'Asesor',
    'Directivo',
    'Mixto',
    'Docente',
]

VA_CONCURSOS = [
    'Otro',
    'Municipios 5ta y 6ta',
    'Municipios Priorizados',
    'CNSC',
    'Directores Territoriales',
    'Personero Municipales',
    'Docentes ESAP',
]

VA_TASA_DEFAULT = {
    'Luego de VRM': 0.7427,
    'Luego de pruebas': 0.1877,
}

# Tasas de conversión a VA cuando el concurso es "Otro": dependen del nivel jerárquico
# y de si la VA ocurre antes o después de pruebas. Fuente: hoja SIMULADOR (Modelo_V2), tabla T39:V46.
VA_TASAS_OTRO_POR_NIVEL = {
    'Asistencial':               {'Luego de VRM': 0.7427968472347812, 'Luego de pruebas': 0.18771533429411502},
    'Tecnico':                   {'Luego de VRM': 0.6045132058176427, 'Luego de pruebas': 0.1526551851381955},
    'Profesional Universitario': {'Luego de VRM': 0.5550441246010209, 'Luego de pruebas': 0.13382810589821642},
    'Especializado':             {'Luego de VRM': 0.5550441246010209, 'Luego de pruebas': 0.13382810589821642},
    'Asesor':                    {'Luego de VRM': 0.7284702001253239, 'Luego de pruebas': 0.20381310677654443},
    'Directivo':                 {'Luego de VRM': 0.6592785260111493, 'Luego de pruebas': 0.16305524531421192},
    'Docente':                   {'Luego de VRM': 0.17553759478355638, 'Luego de pruebas': 0.10017616580310881},
    'Mixto':                     {'Luego de VRM': 0.642015331835756, 'Luego de pruebas': 0.16273232472664984},
}

# Tasas de conversión a VA por convocatoria (cuando el concurso NO es "Otro").
# Las claves coinciden con las opciones del selector de Concurso. Fuente: tabla T25:V31.
VA_TASAS_POR_CONCURSO = {
    'Municipios 5ta y 6ta':     {'Luego de VRM': 0.7359409224607297, 'Luego de pruebas': 0.33284936479128857},
    'Municipios Priorizados':   {'Luego de VRM': 0.18608960944000402, 'Luego de pruebas': 0.08890345679634906},
    'Comisionado CNSC':         {'Luego de VRM': 0.6879733611909116, 'Luego de pruebas': 0.09927526769391486},
    'Directores Territoriales': {'Luego de VRM': 0.6932811446887089, 'Luego de pruebas': 0.1488279658103363},
    'Personeros Municipales':   {'Luego de VRM': 0.9792698301098861, 'Luego de pruebas': 0.1732782185479032},
    'Docentes ESAP':            {'Luego de VRM': 0.17553759478355638, 'Luego de pruebas': 0.10017616580310881},
    'Otro':                     {'Luego de VRM': 0.642015331835756, 'Luego de pruebas': 0.16273232472664984},
}

# Meta diaria de análisis VA por nivel (mesa de expertos). Es la meta de la etapa VA,
# distinta de la meta base VRM. Fuente: tabla T13:U21 / hoja "Meta diaria" (B30:B37).
VA_METAS_POR_NIVEL = {
    'CNSC': 15.0,
    'Asistencial': 20.0,
    'Tecnico': 18.0,
    'Profesional Universitario': 12.0,
    'Especializado': 12.0,
    'Asesor': 10.0,
    'Directivo': 10.0,
    'Docente': 5.0,
    'Mixto': 15.0,
}


def _normalizar_nivel_va(nivel_jerarquico):
    nivel_limpio = str(nivel_jerarquico).strip()
    aliases = {
        'Profesional Especializado': 'Especializado',
        'Profesional Especializada': 'Especializado',
        'Técnico': 'Tecnico',
        'Docentes': 'Docente',
    }
    return aliases.get(nivel_limpio, nivel_limpio)


def obtener_configuracion_va(concurso, nivel_jerarquico, va_antes_pruebas, metodologia):
    """Resuelve tasa de conversión y meta diaria VA replicando la hoja SIMULADOR.

    - La tasa depende del concurso (o del nivel cuando el concurso es "Otro") y de si
      la VA ocurre antes de pruebas; NO depende de la metodología.
    - La meta diaria es 15 carpetas/día en CNSC; en otro caso se toma por nivel.
    """
    columna_tasa = 'Luego de VRM' if va_antes_pruebas == 'SI' else 'Luego de pruebas'
    nivel_clave = _normalizar_nivel_va(nivel_jerarquico)

    if concurso == 'Otro':
        tabla_tasas = VA_TASAS_OTRO_POR_NIVEL.get(nivel_clave, VA_TASA_DEFAULT)
        origen_tasa = f'Otro · {nivel_clave}'
    else:
        tabla_tasas = VA_TASAS_POR_CONCURSO.get(concurso, VA_TASA_DEFAULT)
        origen_tasa = concurso

    tasa = tabla_tasas[columna_tasa]

    if metodologia == 'CNSC':
        meta_diaria = 15.0
        origen_meta = 'CNSC'
    else:
        meta_diaria = VA_METAS_POR_NIVEL.get(nivel_clave, 15.0)
        origen_meta = nivel_clave

    return {
        'tasa': tasa,
        'columna_tasa': columna_tasa,
        'meta_diaria': meta_diaria,
        'origen_meta': origen_meta,
        'origen_tasa': origen_tasa,
    }


# Honorario diario = honorario mensual / 30. Se conserva la precisión completa para
# que el costeo cuadre al peso con la hoja SIMULADOR (tabla T48:X53 de Modelo_V2).
HONORARIOS_MENSUALES_POR_ROL = {
    'Analista': 4738000,
    'Supervisor': 5329000,
    'Auditor': 5684000,
    'Profesional de Apoyo': 5684000,
    'Coordinador': 9031000,
}
HONORARIOS_POR_ROL = {rol: valor / 30 for rol, valor in HONORARIOS_MENSUALES_POR_ROL.items()}

# Factor de días calendario aplicado a los días hábiles en todo el costeo.
FACTOR_CALENDARIO = 1.4

# ------------------------------ MÓDULO JURÍDICO ------------------------------
# Meta diaria de reclamaciones que resuelve un jurista, por fase y por nivel del cargo.
JURIDICO_METAS = {
    'Directivo':           {'VRM': 10, 'Pruebas': 8,  'VA': 5},
    'Profesional':         {'VRM': 10, 'Pruebas': 8,  'VA': 5},
    'Docente':             {'VRM': 6,  'Pruebas': 4,  'VA': 4},
    'Técnico/Asistencial': {'VRM': 15, 'Pruebas': 10, 'VA': 8},
    'Sin experiencia':     {'VRM': 20, 'Pruebas': 10, 'VA': 10},
}
# Margen de reclamaciones sobre la población de cada fase (piso y techo).
JURIDICO_PCT_PISO = 0.08
JURIDICO_PCT_TECHO = 0.15

# Mapea el nivel jerárquico de VRM a la categoría de cargo de Jurídico.
JURIDICO_NIVEL_DESDE_VRM = {
    "Asistencial": "Técnico/Asistencial",
    "Tecnico": "Técnico/Asistencial",
    "Profesional Universitario": "Profesional",
    "Profesional Especializado": "Profesional",
    "Asesor": "Directivo",
    "Directivo": "Directivo",
    "Mixto": "Profesional",
    "Docentes": "Docente",
}

# ------------------- MÓDULO CONSTRUCCIÓN Y CALIFICACIÓN -------------------
# Costos unitarios de la construcción de pruebas (vigencia 2026).
CONSTRUCCION_COSTO_ITEM = 224000       # COP por ítem construido
CONSTRUCCION_VALIDACION_ITEM = 149000  # COP por ítem validado

# Calificación / aplicación de pruebas virtuales (FastTest) — Contrato BOG-1608-2025
# (vigente hasta el 25/11/2026). Valores en USD.
FASTTEST_LICENCIA_ANUAL_USD = 18000.0   # compra + activación de la licencia por 1 año
FASTTEST_CREDITO_USD = 2.50             # valor por crédito (se cobra por persona que pasa VRM)
TRM_DEFAULT = 4000.0                    # tasa de cambio COP por USD (editable)

# Tabla de cargos, niveles, requisitos y valores mensuales 2026 (base para Psicometría).
CARGOS_2026 = [
    {"Cargo": "ASESOR", "Nivel": 6, "Requisitos": "TP + MA + (Más de 161 MER)", "Valor 2026": 19705000},
    {"Cargo": "ASESOR", "Nivel": 5, "Requisitos": "TP + MA + (150-161 MER)", "Valor 2026": 17838000},
    {"Cargo": "ASESOR", "Nivel": 4, "Requisitos": "TP + MA + (138-149 MER)", "Valor 2026": 16533000},
    {"Cargo": "ASESOR", "Nivel": 3, "Requisitos": "TP + MA + (126-137 MER)", "Valor 2026": 15228000},
    {"Cargo": "ASESOR", "Nivel": 2, "Requisitos": "TP + MA + (108-125 MER)", "Valor 2026": 14134000},
    {"Cargo": "ASESOR", "Nivel": 1, "Requisitos": "TP + MA + (102-107 MER)", "Valor 2026": 13487000},
    {"Cargo": "PROFESIONAL ESPECIALIZADO", "Nivel": 9, "Requisitos": "TP + E + (Más de 95 MEP)", "Valor 2026": 13142000},
    {"Cargo": "PROFESIONAL ESPECIALIZADO", "Nivel": 8, "Requisitos": "TP + E + (84-95 MEP)", "Valor 2026": 12322000},
    {"Cargo": "PROFESIONAL ESPECIALIZADO", "Nivel": 7, "Requisitos": "TP + E + (72-83 MEP)", "Valor 2026": 11492000},
    {"Cargo": "PROFESIONAL ESPECIALIZADO", "Nivel": 6, "Requisitos": "TP + E + (60-71 MEP)", "Valor 2026": 10671000},
    {"Cargo": "PROFESIONAL ESPECIALIZADO", "Nivel": 5, "Requisitos": "TP + E + (48-59 MEP)", "Valor 2026": 9851000},
    {"Cargo": "PROFESIONAL ESPECIALIZADO", "Nivel": 4, "Requisitos": "TP + E + (36-47 MEP)", "Valor 2026": 9031000},
    {"Cargo": "PROFESIONAL ESPECIALIZADO", "Nivel": 3, "Requisitos": "TP + E + (24-35 MEP)", "Valor 2026": 8211000},
    {"Cargo": "PROFESIONAL ESPECIALIZADO", "Nivel": 2, "Requisitos": "TP + E + (13-23 MEP)", "Valor 2026": 7391000},
    {"Cargo": "PROFESIONAL ESPECIALIZADO", "Nivel": 1, "Requisitos": "TP + E + (0-12 MEP)", "Valor 2026": 6571000},
    {"Cargo": "PROFESIONAL UNIVERSITARIO", "Nivel": 3, "Requisitos": "TP + (Más de 25 MEP)", "Valor 2026": 5684000},
    {"Cargo": "PROFESIONAL UNIVERSITARIO", "Nivel": 2, "Requisitos": "TP + (13-25 MEP)", "Valor 2026": 5329000},
    {"Cargo": "PROFESIONAL UNIVERSITARIO", "Nivel": 1, "Requisitos": "TP + (0-12 MEP)", "Valor 2026": 4738000},
    {"Cargo": "TECNÓLOGO", "Nivel": 2, "Requisitos": "TFT + TB + (Más de 12 MEL)", "Valor 2026": 4070000},
    {"Cargo": "TECNÓLOGO", "Nivel": 1, "Requisitos": "TFT + TB + (0-12 MEL)", "Valor 2026": 3702000},
    {"Cargo": "TÉCNICO", "Nivel": 3, "Requisitos": "TT + TB + (Más de 19 MEL)", "Valor 2026": 3346000},
    {"Cargo": "TÉCNICO", "Nivel": 2, "Requisitos": "TT + TB + (13-18 MEL)", "Valor 2026": 3104000},
    {"Cargo": "TÉCNICO", "Nivel": 1, "Requisitos": "TT + TB + (0-12 MEL)", "Valor 2026": 2874000},
    {"Cargo": "ASISTENCIAL", "Nivel": 2, "Requisitos": "TB + (Más de 12 MEL)", "Valor 2026": 2634000},
    {"Cargo": "ASISTENCIAL", "Nivel": 1, "Requisitos": "TB + (0-12 MEL)", "Valor 2026": 2392000},
]


def _cargos_df_inicial():
    return pd.DataFrame(CARGOS_2026)


def _perfil_label(cargo, nivel):
    cargo = str(cargo).strip()
    try:
        nivel_txt = f"{int(float(nivel))}"
    except (TypeError, ValueError):
        nivel_txt = str(nivel).strip()
    return f"{cargo} {nivel_txt}".strip()


def _mapa_valores_cargos(cargos_df):
    """Devuelve {label -> valor mensual} a partir de la tabla de cargos (editable)."""
    mapa = {}
    for _, row in cargos_df.iterrows():
        cargo = _valor_texto(row.get("Cargo"))
        nivel = row.get("Nivel")
        valor = _valor_num(row.get("Valor 2026"))
        if not cargo or valor <= 0:
            continue
        mapa[_perfil_label(cargo, nivel)] = valor
    return mapa


# Catálogo estático de la tabla 2026 (para selectores que no editan la tabla).
CARGOS_2026_MAP = {_perfil_label(c["Cargo"], c["Nivel"]): c["Valor 2026"] for c in CARGOS_2026}
CARGOS_2026_LABELS = list(CARGOS_2026_MAP.keys())

# --------------------------- PROYECCIÓN FINANCIERA ---------------------------
# Carga administrativa aplicada sobre el costo directo total del proyecto.
CARGA_ADMIN = [
    ('Equipo Administrativo', 0.0300),
    ('Pólizas', 0.0005),
    ('Imprevistos', 0.0200),
    ('Utilidad o Margen Esperado', 0.3000),
]
CARGA_ADMIN_TOTAL = sum(pct for _, pct in CARGA_ADMIN)  # 0.3505

# Módulos que consolida la vista ejecutiva, en orden de presentación.
PF_MODULOS = ['Logística', 'VRM-VA', 'Jurídico', 'Construcción y Calificación']


def _init_pf_store():
    """Almacén de sesión con el total (mínimo/máximo) de cada módulo.

    Persiste mientras dure la sesión; solo se reinicia con los botones de 'Borrar'.
    """
    if 'pf_store' not in st.session_state:
        st.session_state.pf_store = {m: {'min': 0.0, 'max': 0.0} for m in PF_MODULOS}
    # Garantiza que existan todas las llaves aunque se agreguen módulos nuevos.
    for m in PF_MODULOS:
        st.session_state.pf_store.setdefault(m, {'min': 0.0, 'max': 0.0})
    return st.session_state.pf_store


def pf_registrar(modulo, valor_min, valor_max=None):
    """Registra/actualiza el total de un módulo en el almacén consolidado."""
    store = _init_pf_store()
    if valor_max is None:
        valor_max = valor_min
    store[modulo] = {'min': float(valor_min), 'max': float(valor_max)}


def render_boton_borrar_modulo(modulo, claves_sesion, etiqueta=None):
    """Botón para borrar los valores calculados de un módulo y su registro en Proyección Financiera."""
    etiqueta = etiqueta or f"🗑️ Borrar valores de {modulo}"
    if st.button(etiqueta, key=f"borrar_modulo_{modulo}"):
        for clave in claves_sesion:
            st.session_state.pop(clave, None)
        store = _init_pf_store()
        if modulo in store:
            store[modulo] = {'min': 0.0, 'max': 0.0}
        st.rerun()


def _normalizar_rol_honorarios(rol):
    rol_limpio = str(rol).strip().lower()
    if 'analista' in rol_limpio:
        return 'Analista'
    if 'supervisor' in rol_limpio:
        return 'Supervisor'
    if 'auditor' in rol_limpio:
        return 'Auditor'
    if 'apoyo' in rol_limpio:
        return 'Profesional de Apoyo'
    if 'coordinador' in rol_limpio:
        return 'Coordinador'
    return None


def _con_dedicacion_coordinador(personal_df, ded_coord):
    """Agrega columna 'Dedicación (%)' (100% para todos) y aplica la del coordinador."""
    df = personal_df.copy()
    df["Dedicación (%)"] = 100.0
    mask = df["Rol"].astype(str).str.contains("Coordinador", case=False, na=False)
    df.loc[mask, "Dedicación (%)"] = float(ded_coord)
    return df


def render_ingresos_manual_por_roles(personal_df, prefijo, dias_requeridos, titulo="Costos automáticos por rol"):
    """Valora automáticamente cada rol usando la tabla fija de honorarios por día."""
    st.markdown(f"### {titulo}")
    st.caption("Los valores se calculan usando honorarios diarios fijos por rol y días calendario equivalentes (días hábiles x 1.4).")

    if personal_df is None or personal_df.empty:
        st.info("No hay roles disponibles para calcular ingresos manuales.")
        return

    resultado_rows = []
    dias_calendario = dias_requeridos * 1.4
    tiene_dedicacion = "Dedicación (%)" in personal_df.columns
    for _, row in personal_df.iterrows():
        rol_original = row["Rol"]
        cantidad = float(row["Cantidad"])
        rol_base = _normalizar_rol_honorarios(rol_original)

        if rol_base is None:
            continue

        dedicacion = float(row["Dedicación (%)"]) if tiene_dedicacion else 100.0
        honorario_diario = HONORARIOS_POR_ROL[rol_base]
        subtotal = cantidad * honorario_diario * dias_calendario * (dedicacion / 100.0)
        resultado_rows.append({
            "Rol": rol_original,
            "Cantidad": cantidad,
            "Dedicación (%)": dedicacion,
            "Honorario diario": honorario_diario,
            "Días hábiles": dias_requeridos,
            "Factor calendario": 1.4,
            "Días calendario": dias_calendario,
            "Subtotal": subtotal,
        })

    if not resultado_rows:
        st.info("No se encontraron roles compatibles con la tabla de honorarios.")
        return

    resultado_df = pd.DataFrame(resultado_rows)
    total_ingresos = resultado_df["Subtotal"].sum()
    st.session_state[f"{prefijo}_ingresos_total"] = total_ingresos

    st.markdown("#### Tabla de valoración")
    st.dataframe(
        resultado_df.style.format({
            "Cantidad": "{:,.0f}",
            "Dedicación (%)": "{:,.0f}",
            "Honorario diario": "${:,.2f}",
            "Días hábiles": "{:,.0f}",
            "Factor calendario": "{:,.1f}",
            "Días calendario": "{:,.1f}",
            "Subtotal": "${:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.metric("Total estimado", f"${total_ingresos:,.0f}")

    return st.session_state.get(f"{prefijo}_ingresos_total", 0)


def _juridico_costo_escenario(df, h_jur, h_aud, coord_costo, equipo_base):
    """Recalcula el costo por fase y el total de un escenario a partir de cantidades editables."""
    filas = []
    total = 0.0
    for _, r in df.iterrows():
        juristas = _valor_num(r.get("Juristas"))
        auditores = _valor_num(r.get("Auditores"))
        dias = _valor_num(r.get("Días"))
        costo = (juristas * h_jur + auditores * h_aud) * (dias * FACTOR_CALENDARIO)
        total += costo
        filas.append({
            "Fase": r.get("Fase"), "Reclamaciones": r.get("Reclamaciones"),
            "Juristas": juristas, "Auditores": auditores, "Días": dias, "Costo fase": costo,
        })
    return pd.DataFrame(filas), total + coord_costo + equipo_base


def render_equipo_base(prefijo, titulo="Equipo base (opcional)"):
    """Tabla reutilizable de equipo base (catálogo CARGOS 2026). Devuelve el costo total.

    Costo por recurso = valor mensual del cargo × dedicación (%) × tiempo (meses) × cantidad.
    """
    st.markdown(f"#### {titulo}")
    st.caption("Perfiles adicionales cuyo costo se **suma** al total del módulo. "
               "Costo = valor mensual del cargo × dedicación (%) × tiempo (meses) × cantidad.")
    key_df = f"{prefijo}_equipo_df"
    key_widget = f"{prefijo}_equipo_editor"
    if key_df not in st.session_state:
        st.session_state[key_df] = pd.DataFrame([
            {"Perfil": CARGOS_2026_LABELS[0], "Dedicación (%)": 100, "Tiempo (meses)": 1, "Cantidad": 0},
        ])
    edit = st.data_editor(
        st.session_state[key_df], num_rows="dynamic",
        use_container_width=True, hide_index=True, key=key_widget,
        column_config={
            "Perfil": st.column_config.SelectboxColumn("Perfil (Cargo Nivel)", options=CARGOS_2026_LABELS),
            "Dedicación (%)": st.column_config.NumberColumn("Dedicación (%)", min_value=0, max_value=100, step=5),
            "Tiempo (meses)": st.column_config.NumberColumn("Tiempo (meses)", min_value=0, step=1),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=1),
        },
    )
    costo = 0.0
    for _, row in edit.iterrows():
        perfil = _valor_texto(row.get("Perfil"))
        ded = _valor_num(row.get("Dedicación (%)"))
        tiempo = _valor_num(row.get("Tiempo (meses)"))
        cant = _valor_num(row.get("Cantidad"))
        if perfil in CARGOS_2026_MAP and ded > 0 and tiempo > 0 and cant > 0:
            costo += CARGOS_2026_MAP[perfil] * (ded / 100.0) * tiempo * cant
    if costo > 0:
        st.metric("Costo del equipo base", f"${costo:,.0f}")
    return costo


def render_juridico():
    render_header("Módulo Jurídico", "⚖️")
    st.markdown("### Estimación de reclamaciones y personal jurídico")

    _init_pf_store()
    if "juridico_result" not in st.session_state:
        st.session_state.juridico_result = None

    h_jur = HONORARIOS_POR_ROL["Analista"]
    h_aud = HONORARIOS_POR_ROL["Auditor"]
    h_coord = HONORARIOS_POR_ROL["Coordinador"]

    # ---------------------- Equipo base (catálogo CARGOS 2026) ----------------------
    costo_equipo_base = render_equipo_base("jur")

    # ---------------------- Parámetros de reclamaciones ----------------------
    st.markdown("#### Reclamaciones por fase")
    st.caption("Reclamaciones = margen del 8% (piso) al 15% (techo) sobre la población de cada fase.")
    niveles = list(JURIDICO_METAS.keys())
    inscritos_def = int(st.session_state.get("global_inscritos", 1000)) or 1000
    dias_vrm_def = int(st.session_state.get("global_dias_vrm", 20)) or 20
    dias_va_def = int(st.session_state.get("global_dias_va", 10)) or 10
    va_vol = st.session_state.get("va_volumen")
    # Nivel heredado del módulo VRM (mapeado a las categorías de Jurídico), editable.
    nivel_vrm = st.session_state.get("global_nivel_vrm")
    nivel_def = JURIDICO_NIVEL_DESDE_VRM.get(nivel_vrm, niveles[0])
    idx_nivel = niveles.index(nivel_def) if nivel_def in niveles else 0
    if nivel_vrm:
        st.caption(f"🔗 Nivel tomado de VRM: {nivel_vrm} → {nivel_def} (editable).")
    if st.session_state.get("global_inscritos"):
        st.caption(f"🔗 Inscritos autollenados desde otro módulo: {inscritos_def:,.0f} (editable).")
    if va_vol:
        st.caption(f"🔎 Guía: el volumen calculado en VA fue {int(va_vol):,.0f} aspirantes.")

    with st.form("form_juridico"):
        c1, c2 = st.columns(2)
        with c1:
            nivel = st.selectbox("Nivel del cargo", niveles, index=idx_nivel)
            inscritos = st.number_input("Inscritos (población fase VRM)", min_value=0, value=inscritos_def, step=1)
            poblacion_va = st.number_input("Aspirantes análisis VA (población fase VA)", min_value=0,
                                           value=int(va_vol) if va_vol else 0, step=1)
        with c2:
            dias_vrm = st.number_input("Días hábiles fase VRM", min_value=1, value=dias_vrm_def, step=1)
            dias_va = st.number_input("Días hábiles fase VA", min_value=1, value=dias_va_def, step=1)
        calcular = st.form_submit_button("Calcular Jurídico")

    if calcular:
        metas = JURIDICO_METAS[nivel]
        fases = [
            ("VRM", inscritos, dias_vrm, metas["VRM"]),
            ("VA", poblacion_va, dias_va, metas["VA"]),
        ]
        dias_totales = dias_vrm + dias_va
        costo_coordinador = h_coord * (dias_totales * FACTOR_CALENDARIO)

        escenarios = {}
        for esc_nombre, pct in [("Piso (8%)", JURIDICO_PCT_PISO), ("Techo (15%)", JURIDICO_PCT_TECHO)]:
            filas = []
            for fase, poblacion, dias, meta in fases:
                reclamaciones = math.ceil(poblacion * pct)
                juristas = math.ceil((reclamaciones / dias / meta) * 1.10) if reclamaciones > 0 else 0
                auditores = math.ceil(juristas / 2) if juristas > 0 else 0
                filas.append({
                    "Fase": fase, "Población": poblacion, "Reclamaciones": reclamaciones,
                    "Juristas": juristas, "Auditores": auditores, "Días": dias,
                })
            escenarios[esc_nombre] = pd.DataFrame(filas)

        st.session_state.juridico_result = {"nivel": nivel, "costo_coordinador": costo_coordinador, "metas": metas}
        st.session_state["jur_piso_edit"] = escenarios["Piso (8%)"].copy()
        st.session_state["jur_techo_edit"] = escenarios["Techo (15%)"].copy()
        # Reinicia el estado de los editores para que reflejen el cálculo nuevo.
        st.session_state.pop("jur_piso_editor", None)
        st.session_state.pop("jur_techo_editor", None)

    if st.session_state.juridico_result is None:
        st.info("Completa los datos y presiona 'Calcular Jurídico'.")
        return

    resultado = st.session_state.juridico_result
    coord = resultado["costo_coordinador"]
    metas = resultado.get("metas", {})

    st.divider()
    st.markdown(f"### Resultados (nivel del cargo: {resultado['nivel']})")

    with st.expander("📝 Cómo se calcula"):
        st.markdown(
            f"""
- **Reclamaciones** por fase = población × margen (**8%** piso / **15%** techo).
- **Juristas** = ⌈ reclamaciones ÷ días ÷ meta diaria × 1.1 ⌉. Meta diaria por nivel *{resultado['nivel']}*:
  VRM **{metas.get('VRM','—')}**, VA **{metas.get('VA','—')}**.
- **Auditores** = ⌈ juristas ÷ 2 ⌉.
- **Coordinador** = 1 para todo el módulo; costo = honorario diario × (días VRM+VA) × 1.4.
- **Costo de cada fase** = (juristas × honorario jurista + auditores × honorario auditor) × días × 1.4.
- **Equipo base** = Σ (honorario mensual × dedicación% × meses × cantidad).
- **Total** = Σ costos de fase + coordinador + equipo base.
- Honorario diario = honorario mensual ÷ 30 (Jurista/Analista ${h_jur:,.0f}, Auditor ${h_aud:,.0f}, Coordinador ${h_coord:,.0f}).
            """
        )

    st.caption("Puedes **ajustar a mano** las cantidades de Juristas y Auditores; el costo se recalcula al instante.")
    fmt_costo = {"Reclamaciones": "{:,.0f}", "Juristas": "{:,.0f}", "Auditores": "{:,.0f}",
                 "Días": "{:,.0f}", "Costo fase": "${:,.0f}"}
    totales = {}
    for esc_nombre, key_edit, key_widget in [("Piso (8%)", "jur_piso_edit", "jur_piso_editor"),
                                              ("Techo (15%)", "jur_techo_edit", "jur_techo_editor")]:
        st.markdown(f"#### Escenario {esc_nombre}")
        base_df = st.session_state.get(key_edit)
        edit = st.data_editor(
            base_df, hide_index=True, use_container_width=True, key=key_widget,
            disabled=["Fase", "Población", "Reclamaciones", "Días"],
            column_config={
                "Población": st.column_config.NumberColumn(format="%d"),
                "Reclamaciones": st.column_config.NumberColumn(format="%d"),
                "Juristas": st.column_config.NumberColumn(min_value=0, step=1),
                "Auditores": st.column_config.NumberColumn(min_value=0, step=1),
                "Días": st.column_config.NumberColumn(format="%d"),
            },
        )
        tabla_costo, total_esc = _juridico_costo_escenario(edit, h_jur, h_aud, coord, costo_equipo_base)
        st.dataframe(tabla_costo.style.format(fmt_costo), use_container_width=True, hide_index=True)
        st.metric(f"Costo total {esc_nombre}", f"${total_esc:,.0f}")
        totales[esc_nombre] = total_esc

    st.caption(f"Cada escenario incluye 1 coordinador (${coord:,.0f}) y el equipo base (${costo_equipo_base:,.0f}).")

    st.divider()
    total_piso = totales["Piso (8%)"]
    total_techo = totales["Techo (15%)"]
    pf_registrar("Jurídico", total_piso, total_techo)
    col_a, col_b = st.columns(2)
    col_a.metric("Total Jurídico (piso)", f"${total_piso:,.0f}")
    col_b.metric("Total Jurídico (techo)", f"${total_techo:,.0f}")
    st.caption("Ambos valores se envían a Proyección Financiera como rango mínimo–máximo.")
    render_boton_borrar_modulo(
        "Jurídico",
        ["juridico_result", "jur_piso_edit", "jur_techo_edit", "jur_equipo_df",
         "jur_equipo_editor", "jur_piso_editor", "jur_techo_editor"],
    )


def render_proyeccion_financiera():
    render_header("Proyección Financiera", "💰")
    st.markdown("### Consolidado de costos del proyecto")
    st.caption(
        "Reúne los totales registrados por cada módulo durante la sesión. "
        "Los valores se conservan al navegar entre módulos y solo se reinician con los botones de 'Borrar'."
    )
    store = _init_pf_store()

    filas = []
    total_min = 0.0
    total_max = 0.0
    for modulo in PF_MODULOS:
        vals = store[modulo]
        filas.append({
            "Módulo": modulo,
            "Costo mínimo": vals["min"],
            "Costo máximo": vals["max"],
        })
        total_min += vals["min"]
        total_max += vals["max"]

    st.markdown("#### Costos directos por módulo")
    df = pd.DataFrame(filas)
    st.dataframe(
        df.style.format({"Costo mínimo": "${:,.0f}", "Costo máximo": "${:,.0f}"}),
        use_container_width=True, hide_index=True,
    )

    hay_rango = abs(total_max - total_min) > 0.5
    c1, c2 = st.columns(2)
    if hay_rango:
        c1.metric("Costo directo (mínimo)", f"${total_min:,.0f}")
        c2.metric("Costo directo (máximo)", f"${total_max:,.0f}")
    else:
        c1.metric("Costo directo total", f"${total_max:,.0f}")

    st.markdown("#### Carga administrativa (35.05%)")
    carga_rows = [
        {"Concepto": nombre, "%": pct, "Monto (mín)": total_min * pct, "Monto (máx)": total_max * pct}
        for nombre, pct in CARGA_ADMIN
    ]
    carga_rows.append({
        "Concepto": "Total Carga Administrativa", "%": CARGA_ADMIN_TOTAL,
        "Monto (mín)": total_min * CARGA_ADMIN_TOTAL, "Monto (máx)": total_max * CARGA_ADMIN_TOTAL,
    })

    def _resaltar_total_carga(row):
        # Resalta la fila del total para diferenciarla de los conceptos.
        if row["Concepto"] == "Total Carga Administrativa":
            return ["background-color: #FFE8CC; color: #7a3e00; font-weight: 700"] * len(row)
        return [""] * len(row)

    st.dataframe(
        pd.DataFrame(carga_rows).style
        .apply(_resaltar_total_carga, axis=1)
        .format({"%": "{:.2%}", "Monto (mín)": "${:,.0f}", "Monto (máx)": "${:,.0f}"}),
        use_container_width=True, hide_index=True,
    )
    st.caption("La fila resaltada es el **total de la carga administrativa** (suma de los 4 conceptos), no el valor total del proyecto.")

    valor_total_min = total_min * (1 + CARGA_ADMIN_TOTAL)
    valor_total_max = total_max * (1 + CARGA_ADMIN_TOTAL)
    st.markdown("#### Valor total del proyecto")
    st.caption("Valor Total = Costos Directos + Carga Administrativa (Directos × 1.3505).")
    d1, d2 = st.columns(2)
    if hay_rango:
        d1.metric("Valor total (mínimo)", f"${valor_total_min:,.0f}")
        d2.metric("Valor total (máximo)", f"${valor_total_max:,.0f}")
    else:
        d1.metric("Valor total del proyecto", f"${valor_total_max:,.0f}")

    st.divider()
    st.markdown("#### Gestión de datos")
    st.caption(
        "Nota: cada módulo vuelve a registrar su total al visitarlo mientras tenga datos calculados. "
        "Usa 'Borrar' para poner en cero un módulo que no aplique o para reiniciar todo."
    )
    b1, b2 = st.columns(2)
    with b1:
        modulo_borrar = st.selectbox("Borrar el total de un módulo", PF_MODULOS, key="pf_borrar_sel")
        if st.button("🗑️ Borrar módulo seleccionado"):
            store[modulo_borrar] = {"min": 0.0, "max": 0.0}
            st.rerun()
    with b2:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("🗑️ Borrar TODO"):
            st.session_state.pf_store = {m: {"min": 0.0, "max": 0.0} for m in PF_MODULOS}
            st.rerun()


def _valor_num(v):
    """Convierte un valor de celda (posible None/NaN) a float seguro."""
    if v is None:
        return 0.0
    try:
        if isinstance(v, float) and math.isnan(v):
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _valor_texto(v):
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v).strip()


def render_construccion():
    render_header("Módulo Construcción y Calificación", "🏗️📝")
    st.markdown("### Componente de construcción y evaluación (vigencia 2026)")

    _init_pf_store()

    # ---------------------- 1. Construcción de pruebas ----------------------
    st.markdown("#### 1. Construcción de pruebas")
    st.caption(
        f"Costo unitario 2026: construcción ${CONSTRUCCION_COSTO_ITEM:,.0f}/ítem · "
        f"validación ${CONSTRUCCION_VALIDACION_ITEM:,.0f}/ítem. "
        "La cantidad de ítems la define el equipo de Psicometría."
    )
    cantidad_items = st.number_input(
        "Cantidad de ítems", min_value=0, value=0, step=1, key="constr_cantidad_items"
    )
    costo_construccion = cantidad_items * CONSTRUCCION_COSTO_ITEM
    costo_validacion = cantidad_items * CONSTRUCCION_VALIDACION_ITEM
    total_pruebas = costo_construccion + costo_validacion
    p1, p2, p3 = st.columns(3)
    p1.metric("Costo construcción", f"${costo_construccion:,.0f}")
    p2.metric("Costo validación", f"${costo_validacion:,.0f}")
    p3.metric("Total construcción de pruebas", f"${total_pruebas:,.0f}")

    # ---------------------- 2. Equipo de Psicometría ----------------------
    st.markdown("#### 2. Equipo de Psicometría")

    # Tabla de cargos: es una referencia; se puede editar dentro del expander (opcional).
    if "constr_cargos_df" not in st.session_state:
        st.session_state.constr_cargos_df = _cargos_df_inicial()
    with st.expander("🔧 Ajustar tabla de cargos y valores 2026 (opcional)"):
        st.caption("Puedes agregar o modificar cargos; el selector de Perfil se actualiza con estos valores.")
        cargos_edit = st.data_editor(
            st.session_state.constr_cargos_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="constr_cargos_editor",
            column_config={
                "Cargo": st.column_config.TextColumn("Cargo"),
                "Nivel": st.column_config.NumberColumn("Nivel", min_value=0, step=1),
                "Requisitos": st.column_config.TextColumn("Requisitos"),
                "Valor 2026": st.column_config.NumberColumn("Valor 2026", min_value=0, step=1000, format="$%d"),
            },
        )

    mapa_valores = _mapa_valores_cargos(cargos_edit)
    perfiles = list(mapa_valores.keys())
    if not perfiles:
        st.warning("Agrega al menos un cargo con 'Valor 2026' en la tabla para poder estimar el equipo de Psicometría.")
        perfiles = [""]

    st.caption("Agrega los recursos del equipo. Costo por recurso = valor mensual del cargo × dedicación (%) × tiempo (meses) × cantidad.")

    if "psico_df" not in st.session_state:
        st.session_state.psico_df = pd.DataFrame([
            {"Descripción/Rol": "", "Perfil": "",
             "Dedicación (%)": 0, "Tiempo (meses)": 0, "Cantidad": 0},
        ])

    edited = st.data_editor(
        st.session_state.psico_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="constr_psico_editor",
        column_config={
            "Descripción/Rol": st.column_config.TextColumn("Descripción / Rol"),
            "Perfil": st.column_config.SelectboxColumn("Perfil (Cargo Nivel)", options=perfiles),
            "Dedicación (%)": st.column_config.NumberColumn("Dedicación (%)", min_value=0, max_value=100, step=5),
            "Tiempo (meses)": st.column_config.NumberColumn("Tiempo (meses)", min_value=0, step=1),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=1),
        },
    )

    # ---------------------- 3. Calificación — pruebas virtuales (FastTest) ----------------------
    st.markdown("#### 3. Calificación — aplicación de pruebas virtuales (FastTest)")
    st.caption(
        "Contrato BOG-1608-2025 (vigente hasta 25/11/2026). Valores en USD, convertidos a COP con la TRM. "
        f"Licencia anual US$ {FASTTEST_LICENCIA_ANUAL_USD:,.0f}; crédito US$ {FASTTEST_CREDITO_USD:,.2f} por persona."
    )
    if "constr_trm" not in st.session_state:
        st.session_state["constr_trm"] = TRM_DEFAULT
    if "constr_pct_licencia" not in st.session_state:
        st.session_state["constr_pct_licencia"] = 0
    va_vol_constr = int(st.session_state.get("va_volumen", 0) or 0)
    if "constr_personas_creditos" not in st.session_state:
        st.session_state["constr_personas_creditos"] = va_vol_constr
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        trm = st.number_input("TRM (COP por USD)", min_value=0.0, step=50.0, key="constr_trm")
    with fc2:
        pct_licencia = st.number_input("% de la licencia que se cobra", min_value=0, max_value=100, step=5,
                                       key="constr_pct_licencia")
    with fc3:
        personas_creditos = st.number_input("Personas que pasan VRM (créditos)", min_value=0, step=1,
                                            key="constr_personas_creditos")
    if va_vol_constr:
        st.caption(f"🔗 Volumen VA (los que pasan VRM): {va_vol_constr:,.0f} — autollenado, editable.")

    licencia_usd = FASTTEST_LICENCIA_ANUAL_USD * (pct_licencia / 100.0)
    creditos_usd = personas_creditos * FASTTEST_CREDITO_USD
    licencia_cop = licencia_usd * trm
    creditos_cop = creditos_usd * trm
    total_calificacion_cop = licencia_cop + creditos_cop
    fast_df = pd.DataFrame([
        {"Concepto": f"Licencia FastTest (anual × {pct_licencia:.0f}%)", "USD": licencia_usd, "COP": licencia_cop},
        {"Concepto": f"Créditos ({personas_creditos:,.0f} pers. × US$ {FASTTEST_CREDITO_USD:.2f})", "USD": creditos_usd, "COP": creditos_cop},
    ])

    # ---------------------- Cálculo en vivo (sin botón: todo se actualiza al instante) ----------------------
    filas_validas = []
    incompletas = 0
    for _, row in edited.iterrows():
        descr = _valor_texto(row.get("Descripción/Rol"))
        perfil = _valor_texto(row.get("Perfil"))
        ded = _valor_num(row.get("Dedicación (%)"))
        tiempo = _valor_num(row.get("Tiempo (meses)"))
        cant = _valor_num(row.get("Cantidad"))
        if not perfil and not descr and ded == 0 and tiempo == 0 and cant == 0:
            continue
        if not perfil or perfil not in mapa_valores or ded <= 0 or tiempo <= 0 or cant <= 0:
            incompletas += 1
            continue
        filas_validas.append((descr, perfil, ded, tiempo, cant))

    psico_rows = []
    total_psico = 0.0
    for descr, perfil, ded, tiempo, cant in filas_validas:
        honorario = mapa_valores[perfil]
        costo = honorario * (ded / 100.0) * tiempo * cant
        total_psico += costo
        psico_rows.append({
            "Descripción/Rol": descr, "Perfil": perfil,
            "Honorario mensual": honorario, "Dedicación (%)": ded,
            "Tiempo (meses)": tiempo, "Cantidad": cant, "Costo": costo,
        })
    psico_df_result = pd.DataFrame(psico_rows)

    total_modulo = total_pruebas + total_psico + total_calificacion_cop
    pf_registrar("Construcción y Calificación", total_modulo)

    if incompletas > 0:
        st.warning(f"Hay {incompletas} recurso(s) de Psicometría con datos faltantes "
                   "(Perfil, Dedicación, Tiempo o Cantidad); no se incluyeron en el total.")

    st.divider()
    st.markdown("### Resultados")
    if not psico_df_result.empty:
        st.markdown("#### Detalle del Equipo de Psicometría")
        st.dataframe(
            psico_df_result.style.format({
                "Honorario mensual": "${:,.0f}", "Dedicación (%)": "{:,.0f}",
                "Tiempo (meses)": "{:,.0f}", "Cantidad": "{:,.0f}", "Costo": "${:,.0f}",
            }),
            use_container_width=True, hide_index=True,
        )
    st.markdown("#### Detalle de Calificación (FastTest)")
    st.dataframe(
        fast_df.style.format({"USD": "US$ {:,.2f}", "COP": "${:,.0f}"}),
        use_container_width=True, hide_index=True,
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Construcción de pruebas", f"${total_pruebas:,.0f}")
    m2.metric("Psicometría", f"${total_psico:,.0f}")
    m3.metric("Calificación (FastTest)", f"${total_calificacion_cop:,.0f}")
    m4.metric("Total del módulo", f"${total_modulo:,.0f}")
    render_boton_borrar_modulo(
        "Construcción y Calificación",
        ["psico_df", "constr_psico_editor", "constr_cantidad_items",
         "constr_trm", "constr_pct_licencia", "constr_personas_creditos"],
    )


# ==============================================================================
# 1. LÓGICA DEL NEGOCIO (FUNCIONES DEL MODELO PARAMÉTRICO)
# ==============================================================================

@st.cache_data
def obtener_costos_tecnologia(cantidad_equipos_base, n_sitios, requiere_alquiler):
    """
    Calcula costos de alquiler basado en la cantidad solicitada MANUALMENTE por el usuario.
    El sistema agrega automáticamente el 10% de reserva técnica (backup).
    """
    if not requiere_alquiler or cantidad_equipos_base == 0:
        return {'Total': 0, 'Detalle': {}}

    # 1. CÁLCULO DE EQUIPOS TOTALES
    # Base solicitada + 10% Backup (Mínimo 1 equipo de backup por sitio si es muy poco)
    n_backup = math.ceil(cantidad_equipos_base * 0.10)
    
    # Regla de seguridad: Mínimo 2 de backup por sitio si la cantidad es muy baja
    if n_backup < (n_sitios * 2): 
        n_backup = n_sitios * 2
        
    total_equipos_facturables = cantidad_equipos_base + n_backup
    
    # 2. PRECIOS POR RANGO (Economía de escala sobre el TOTAL facturable)
    # Rango 1: 0-1000 | R2: 1001-1500 | R3: >1500
    limites = (1000, 1500)

    # Alquiler
    p_alquiler = get_precio_rango(total_equipos_facturables, limites, (68000, 55000, 48000))
    # Logística
    p_logistica = get_precio_rango(total_equipos_facturables, limites, (15000, 12000, 10000))
    # Montaje
    p_montaje = get_precio_rango(total_equipos_facturables, limites, (7000, 5000, 4000))
    
    # 3. TOTALES
    costo_alquiler = total_equipos_facturables * p_alquiler
    costo_logistica = total_equipos_facturables * p_logistica
    costo_montaje = total_equipos_facturables * p_montaje
    
    total_tech = costo_alquiler + costo_logistica + costo_montaje
    
    return {
        'Total': total_tech,
        'Detalle': {
            'Alquiler Equipos': costo_alquiler,
            'Logística Hardware': costo_logistica,
            'Montaje y Config': costo_montaje,
            'Equipos Base': cantidad_equipos_base,
            'Backup (10%)': n_backup,
            'Total Equipos Facturados': total_equipos_facturables
        }
    }

@st.cache_data
def obtener_costo_unitario_logistico(ciudad, n_aspirantes):
    """
    Retorna el Costo Unitario de Transporte exacto según el volumen (Rango 1, 2 o 3).
    Fuente: Recopilado_Perso.xlsx (Filas de APLICACIÓN DE PRUEBA).
    Lógica: Busca la ciudad y aplica el precio según la cantidad de aspirantes.
    """
    ciudad_key = ciudad.title()
    # 1. Identificar datos de la ciudad (Normalización de nombres)
    datos_ciudad = None
    for k, v in TARIFARIO_DINAMICO.items():
        if k in ciudad_key or ciudad_key in k:
            datos_ciudad = v
            break
    
    if not datos_ciudad:
        # Fallback: Promedio nacional de Rango 3 si la ciudad no está listada
        return 65000 
        
    # 2. Seleccionar precio según Rango de volumen
    # Tupla: (Limite_Superior, Precio)
    r1_lim, r1_price = datos_ciudad[0]
    r2_lim, r2_price = datos_ciudad[1]
    r3_lim, r3_price = datos_ciudad[2]
    
    if n_aspirantes <= r1_lim:
        return r1_price
    elif n_aspirantes <= r2_lim:
        return r2_price
    else:
        # Volumen alto (Rango 3 o superior) -> Precio más económico
        return r3_price

@st.cache_data
def obtener_costos_disposicion_final(n_aspirantes):
    """
    Calcula costos de custodia y destrucción segura de material.
    Estimación: $1,500 COP por aspirante (Custodia 3 meses + Destrucción Certificada).
    """
    # Tarifa estimada por aspirante para gestión documental segura
    tarifa_custodia = 1000 
    tarifa_destruccion = 500
    total = n_aspirantes * (tarifa_custodia + tarifa_destruccion)
    return {
        'Total': total,
        'Detalle': {
            'Custodia Temporal': n_aspirantes * tarifa_custodia,
            'Destrucción Certificada': n_aspirantes * tarifa_destruccion
        }
    }

def obtener_costo_transporte(ciudad, n_aspirantes):
    """
    Wrapper que calcula el costo total de transporte basado en el unitario.
    """
    unitario = obtener_costo_unitario_logistico(ciudad, n_aspirantes)
    return unitario * n_aspirantes


# ==============================================================================
# FUNCIÓN DE MATERIALES DETALLADOS (CON RANGOS)
# ==============================================================================

def get_precio_rango(cantidad, limites, precios):
    """
    Selecciona el precio según el rango en el que cae la cantidad.
    limites: tupla (limite_r1, limite_r2)
    precios: tupla (precio_r1, precio_r2, precio_r3)
    """
    lim_r1, lim_r2 = limites
    p_r1, p_r2, p_r3 = precios
    
    if cantidad <= lim_r1:
        return p_r1
    elif cantidad <= lim_r2:
        return p_r2
    else:
        return p_r3

@st.cache_data
def obtener_detalles_materiales(n_aspirantes, n_salones, n_sitios, total_staff, n_formas=1):
    """
    Calcula los costos desglosados exactamente en las categorías solicitadas.
    Precios dinámicos basados en Recopilado_Perso.xlsx.
    """
    
    # 1. INFRAESTRUCTURA (Setup Inicial)
    # Corresponde a "Diagramación de cuadernillo en formato editorial"
    # Costo fijo único del proyecto (Source 2)
    precio_unitario_diseno = 1599239
    # El costo se multiplica por la cantidad de versiones distintas del examen
    costo_infraestructura = precio_unitario_diseno * n_formas
    
    # 2. EMPAQUE (Costo - Cantidad)
    # Empaque individual (Cuadernillo + HR).
    # Precios dinámicos por volumen de aspirantes (Source 18).
    # Rangos: 0-1000 | 1001-1500 | >1500
    lim_asp = (1000, 1500)
    p_empaque = get_precio_rango(n_aspirantes, lim_asp, (2687, 2598, 2516))
    
    # Sumamos un pequeño margen para "Empaque materiales adicionales" (Cajas/Tulas)
    # que no tienen precio en el CSV, estimado en $100 pesos por aspirante.
    costo_empaque_total = n_aspirantes * (p_empaque + 100)

    # 3. KIT DACTILOSCOPISTA
    # Cantidad: 1 por cada 4 salones (aprox)
    n_dactilos = math.ceil(n_salones / 4)
    # Precio Harmonic Mean (Source 17) para garantizar cobertura
    p_kit_dactilo = 40669 
    costo_kit_dactilo = n_dactilos * p_kit_dactilo

    # 4. KIT DE APLICACIÓN (Por Salón)
    # Marcador, Esfero, Cinta, Lápiz, Borrador (Source 15/39)
    p_kit_app = 17850
    costo_kit_app = n_salones * p_kit_app

    # 5. KIT DE ASEO (Limpieza)
    # Componentes: Escoba, Trapero, Recogedor, Jabón Polvo, Bolsas.
    # Cantidad: 1 por cada auxiliar de aseo (1 cada 6 salones)
    n_personal_aseo = math.ceil(n_salones / 6)
    # Precios Rango 3 (Volumen):
    p_aseo = 14278 + 27467 + 12464 + 15635 + 26885 # = $96,729
    costo_kit_aseo = n_personal_aseo * p_aseo

    # 6. KIT PARA BAÑOS (Higiene)
    # Componentes: Papel Higiénico, Toallas de Mano, Jabón Líquido.
    # Precios Rango 3 (Volumen):
    p_banos = 3743 + 13807 + 17497 # = $35,047
    costo_kit_banos = n_personal_aseo * p_banos

    # 7. LECTURA (Procesamiento)
    # Lectura óptica y digitalización (Source 23)
    # Variable crítica: Baja de $11,900 a $5,439 según volumen.
    p_lectura = get_precio_rango(n_aspirantes, lim_asp, (11900, 6120, 5439))
    costo_lectura = n_aspirantes * p_lectura

    # 8. MATERIAL EXAMEN APLICACIÓN (Lo que usa el aspirante)
    # Cuadernillo + Hoja de Respuesta + Hoja de Operaciones
    p_cuad = get_precio_rango(n_aspirantes, lim_asp, (5705, 4909, 4744))
    
    # Hoja Respuesta (Ajuste de anomalía en CSV Rango 2):
    if n_aspirantes <= 1000:
        p_hr = 192
    elif n_aspirantes <= 1500:
        p_hr = 150  # Suavizado manual
    else:
        p_hr = 36
    
    # Hoja de notas (asumimos costo similar a una hoja de respuesta simple o fotocopia)
    p_notas = 50 
    
    # CASO B: Cada aspirante recibe TODAS las formas de prueba
    # El material de examen (cuadernillo + HR + notas) se multiplica por n_formas
    # Ejemplo: 3 formas = 3 cuadernillos por aspirante
    costo_mat_examen_app = n_aspirantes * (p_cuad + p_hr + p_notas) * n_formas

    # 9. MATERIAL EXAMEN EXHIBICIÓN (Documentos legales y copias)
    # Clave de Respuesta ($978) + Acuerdo Confidencialidad ($680) + Copia HR ($319)
    # La CLAVE DE RESPUESTA se multiplica por formas (1 clave por cada forma)
    # La Copia HR también se multiplica (1 por cada forma que presenta el aspirante)
    p_clave_resp = 978
    p_acuerdo = 680  # Acuerdo confidencialidad (1 por aspirante, no por forma)
    p_copia_hr = 319  # Copia HR (1 por cada forma)
    
    # Clave de respuesta: n_formas claves × costo × cantidad de juegos necesarios por sitio
    costo_claves_respuesta = n_formas * p_clave_resp * n_sitios * 2  # 2 juegos por sitio (original + backup)
    costo_acuerdos = n_aspirantes * p_acuerdo  # 1 acuerdo por aspirante
    costo_copias_hr = n_aspirantes * p_copia_hr * n_formas  # 1 copia HR por cada forma
    costo_mat_examen_exhib = costo_claves_respuesta + costo_acuerdos + costo_copias_hr

    # 10. MATERIAL APLICACIÓN (Papelería Técnica / Señalización)
    # Listados, Actas, Afiches, Rótulos, Informes.
    # Dinámico según cantidad de salones (Rangos 40, 60)
    lim_papel = (40, 60)
    
    # Precios dinámicos (Actas y Listados)
    p_listados = get_precio_rango(n_salones, lim_papel, (476, 357, 309))
    p_actas = get_precio_rango(n_salones, lim_papel, (476, 357, 309))
    p_afiches = get_precio_rango(n_salones, lim_papel, (952, 766, 759))
    
    # Precios fijos/promedio (Rótulos, Informes)
    p_rotulos = 2674
    p_informes = 279
    p_puerta = 213
    
    costo_material_app = (
        (n_sitios * 4 * p_puerta) +         # Listados Puerta
        (n_salones * p_listados) +          # Listados Asistencia
        (n_salones * p_actas) +             # Actas Sesión
        (n_sitios * 2 * p_informes) +       # Informes Delegado/Coord
        (n_salones * 2 * p_afiches) +       # Afiches (Prohibido/Tiempos)
        (n_sitios * p_rotulos) +            # Rótulo Sitio
        (n_salones * p_rotulos)             # Rótulo Salón
    )

    # 11. CREDENCIALES (Parte de Material Aplicación o Exhibición según se vea)
    # Lo separamos para claridad pero se suma al total de materiales
    p_cred = get_precio_rango(total_staff, (60, 120), (3570, 3332, 3213))
    costo_credenciales = total_staff * p_cred

    # --- DISPOSICIÓN FINAL ---
    # Custodia y Destrucción (Source Final CSV)
    if n_aspirantes > 1000:
        p_cust = 486818
        p_dest = 1428
    else:
        p_cust = 194727
        p_dest = 2618
    costo_disposicion = (p_cust * 2) + (n_aspirantes * p_dest)

    # SUMA TOTAL DE MATERIALES E INSUMOS
    # Nota: No sumamos Nómina ni Transporte aquí, eso va en la función principal
    total_general_materiales = (
        costo_infraestructura + costo_empaque_total + costo_kit_dactilo +
        costo_kit_app + costo_kit_aseo + costo_kit_banos + costo_lectura +
        costo_mat_examen_app + costo_mat_examen_exhib + costo_material_app +
        costo_credenciales + costo_disposicion
    )

    return total_general_materiales, {
        'Infraestructura (Diagramación)': costo_infraestructura,
        'Empaque': costo_empaque_total,
        'Kit Dactiloscopista': costo_kit_dactilo,
        'Kit de aplicación': costo_kit_app,  # Validado: Insumos de aula (Marcador, Cinta, etc.) por Salón
        'Kit de aseo': costo_kit_aseo,
        'Kit para baños': costo_kit_banos,
        'Lectura': costo_lectura,
        'Material examen aplicación': costo_mat_examen_app,
        'Material examen exhibición': costo_mat_examen_exhib,
        'Material aplicación (Papelería)': costo_material_app + costo_credenciales, # Sumamos credenciales aquí
        'Disposición Final': costo_disposicion
    }

def calcular_modelo_parametrico(n_aspirantes, ciudad, tipo_prueba, requiere_alquiler=False, n_equipos_alquiler=0, n_formas=1):
    """
    Calcula el presupuesto total integrando Logística, Nómina, Materiales (8 Cats),
    Tecnología, Aseo y Transporte.
    """
    
    # --- A. MOTOR LÓGICO (INFRAESTRUCTURA) ---
    # Reglas base: 1 sitio x 500 pax, 1 salón x 25 pax
    n_sitios = math.ceil(n_aspirantes / 500)
    n_salones = math.ceil(n_aspirantes / 25) 
    
    # --- B. PERSONAL LOGÍSTICO (CANTIDADES Y COSTOS) ---
    # Definición de reglas según modalidad
    if "Virtual" in tipo_prueba:
        div_coord = 4           # Mayor supervisión (1 coord x 4 salones)
        mul_jefe = 2            # Doble control (2 jefes x salón)
        n_custodia = 0          # No aplica en virtual
        n_ing = n_sitios        # 1 Ingeniero por sitio obligatorio
        # Riesgo mayor en virtual por fallos técnicos
        factor_riesgo = 1.15    
    else:
        div_coord = 6           # Estándar (1 coord x 6 salones)
        mul_jefe = 1            # Estándar (1 jefe x salón)
        n_custodia = n_sitios   # 1 Custodio por sitio (Papel)
        n_ing = 0               # No requiere ingeniero
        requiere_alquiler = False # Forzamos apagado de alquiler
        factor_riesgo = 1.10

    # Cálculo de cantidades de Staff
    n_coord_aula = math.ceil(n_salones / div_coord)
    n_jefes_salon = n_salones * mul_jefe
    n_aseo = math.ceil(n_salones / 6)
    n_orientadores = math.ceil(n_salones / 6)
    n_dactilo = math.ceil(n_salones / 4)
    n_delegado_prueba = n_sitios
    n_coord_sitio = n_sitios
    n_enfermeros = n_sitios
    n_seguridad = n_sitios * 2

    # Lista de Nómina con Tarifas (Source 63-65 CSV)
    detalle_nomina = [
        {'Cargo': 'Delegado Prueba', 'Cant': n_delegado_prueba, 'Val': 300000},
        {'Cargo': 'Delegado Custodia', 'Cant': n_custodia, 'Val': 300000},
        {'Cargo': 'Coord. Sitio', 'Cant': n_coord_sitio, 'Val': 283333},
        {'Cargo': 'Coord. Aulas', 'Cant': n_coord_aula, 'Val': 283333},
        {'Cargo': 'Jefe Salón', 'Cant': n_jefes_salon, 'Val': 200000},
        {'Cargo': 'Orientador', 'Cant': n_orientadores, 'Val': 200000},
        {'Cargo': 'Ing. Sistemas', 'Cant': n_ing, 'Val': 283333},
        {'Cargo': 'Dactiloscopista', 'Cant': n_dactilo, 'Val': 200000},
        {'Cargo': 'Aux. Aseo', 'Cant': n_aseo, 'Val': 200000},
        {'Cargo': 'Seguridad', 'Cant': n_seguridad, 'Val': 200000},
        {'Cargo': 'Enfermería', 'Cant': n_enfermeros, 'Val': 200000}
    ]
    
    # Filtrar roles en 0 y calcular totales
    detalle_nomina = [d for d in detalle_nomina if d['Cant'] > 0]
    total_nomina = sum([d['Cant'] * d['Val'] for d in detalle_nomina])
    total_staff = sum([d['Cant'] for d in detalle_nomina])

    # --- C. MATERIALES DETALLADOS (8 CATEGORÍAS) ---
    # Llamada a la función auditada que devuelve el costo total y el desglose
    total_materiales_general, desglose_mat = obtener_detalles_materiales(
        n_aspirantes, n_salones, n_sitios, total_staff, n_formas
    )

    # --- D. KITS DE ASEO Y BAÑOS ---
    # Calculados por separado para visibilidad (Precios Rango 3)
    p_kit_limpieza = 96729  # Escoba, trapero, jabón polvo, bolsas...
    p_kit_banos = 35047     # Papel, toallas, jabón manos...
    
    total_kit_limpieza = n_aseo * p_kit_limpieza
    total_kit_banos = n_aseo * p_kit_banos

    # --- E. ALQUILER DE TECNOLOGÍA (Variable Manual) ---
    # Llama a la función de rangos tecnológicos
    res_tech = obtener_costos_tecnologia(n_equipos_alquiler, n_sitios, requiere_alquiler)
    total_tech = res_tech['Total']

    # --- F. TRANSPORTE Y DISTRIBUCIÓN ---
    # Llama a la función de 27 ciudades x 3 rangos
    total_transporte = obtener_costo_transporte(ciudad, n_aspirantes)

    # --- G. CONSOLIDACIÓN DE TOTALES ---
    # Suma de todos los componentes mayores
    total_proyecto = (
        total_nomina + 
        total_materiales_general + # Incluye las 8 categorías + Disposición Final
        total_kit_limpieza + 
        total_kit_banos + 
        total_tech + 
        total_transporte
    )
    
    # Intervalos de confianza (Presupuesto sugerido)
    total_min = total_proyecto * 0.95
    total_max = total_proyecto * factor_riesgo

    # --- RETORNO DE ESTRUCTURA DE DATOS ---
    return {
        # 1. Datos Físicos
        'logistica': {
            'Sitios': n_sitios, 
            'Salones': n_salones, 
            'Staff Total': total_staff,
            'PCs Alquilados': res_tech['Detalle'].get('Total Equipos Facturados', 0)
        },
        
        # 2. Detalle Nómina (Lista para DataFrame)
        'detalle_nomina': [
            {'Cargo': d['Cargo'], 'Cantidad': d['Cant'], 'Tarifa': d['Val'], 'Subtotal': d['Cant']*d['Val']} 
            for d in detalle_nomina
        ],
        
        # 3. Desglose Financiero (Claves exactas para el Reporte)
        'financiero': {
            # Bloque Personal
            'Personal Logístico': total_nomina,
            
            # Bloque Infraestructura y Tecnología
            'Infraestructura (Diagramación)': desglose_mat['Infraestructura (Diagramación)'],
            'Tecnología (Alquiler PC)': total_tech,
            
            # Bloque Materiales Examen
            'Material Examen Aplicación': desglose_mat['Material examen aplicación'],
            'Material Examen Exhibición': desglose_mat['Material examen exhibición'],
            'Lectura y Procesamiento': desglose_mat['Lectura'],
            
            # Bloque Logística de Sitio
            'Material Aplicación (Papelería)': desglose_mat['Material aplicación (Papelería)'],
            'Kit de Aplicación': desglose_mat['Kit de aplicación'],
            'Kit Dactiloscopista': desglose_mat['Kit Dactiloscopista'],
            'Kit de Aseo': total_kit_limpieza,
            'Kit para Baños': total_kit_banos,
            
            # Bloque Distribución
            'Empaque': desglose_mat['Empaque'],
            'Transporte y Distribución': total_transporte,
            'Disposición Final': desglose_mat['Disposición Final'],
            
            # TOTAL
            'TOTAL_BASE': total_proyecto
        },
        
        # 4. Indicadores Unitarios
        'unitario': total_proyecto / n_aspirantes,
        'unitario_max': total_max / n_aspirantes,
        
        # 5. Rangos de Riesgo
        'intervalo': {
            'min': total_min,
            'max': total_max,
            'gap': total_max - total_min
        }
    }

# ==============================================================================
# INTERFAZ DE USUARIO (SIDEBAR)
# ==============================================================================

# Logo y título institucional
st.sidebar.image("https://www1.funcionpublica.gov.co/documents/28587425/0/Logo-Esap-2.jpg/0124afde-6f53-1142-aa8e-c6ec532420d8?t=1539733495049", use_container_width=True)

st.sidebar.markdown(
    """
    <div style="text-align: center; padding: 1rem; margin-bottom: 1rem; 
                background: rgba(255,255,255,0.1); border-radius: 12px;">    
        <p style="color: #ffffff; font-size: 0.85rem; margin: 0.5rem 0 0 0; opacity: 0.9;">
            Sistema de Costeo de Concursos
        </p>
        <p style="color: #ffffff; font-size: 0.7rem; margin: 0.3rem 0 0 0; opacity: 0.7;">
            v3.0 | Abril 2026
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Navegación por módulos
st.sidebar.title("🧭 Módulos")

modulo_activo = st.sidebar.radio(
    "Selecciona un módulo",
    ["Inicio", "Logística", "VRM-VA", "Jurídico", "Construcción y Calificación", "Proyección Financiera"],
    index=0,
    format_func=lambda opcion: {
        "Inicio": "🏛️ Inicio",
        "Logística": "🚚 Logística",
        "VRM-VA": "🧪 VRM-VA",
        "Jurídico": "⚖️ Jurídico",
        "Construcción y Calificación": "🏗️📝 Construcción y Calificación",
        "Proyección Financiera": "💰 Proyección Financiera",
    }[opcion],
)

st.sidebar.markdown(
    """
    <div style="background: rgba(0,102,204,0.3); padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0;">
        <p style="color: #ffffff; margin: 0; font-size: 0.95rem; font-weight: 600;">
            📘 Proyecto modular
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("---")

estado_actual = {
    "Inicio": "🏛️ Vista General del Proyecto",
    "Logística": "🚚 Módulo de Logística",
    "VRM-VA": "🧪 Módulo VRM-VA",
    "Jurídico": "⚖️ Módulo Jurídico",
    "Construcción y Calificación": "🏗️📝 Módulo Construcción y Calificación",
    "Proyección Financiera": "💰 Proyección Financiera",
}[modulo_activo]

st.sidebar.markdown(
    f"""
    <div style="background: rgba(255,140,0,0.2); padding: 0.8rem; border-radius: 8px; margin-bottom: 1rem;">
        <p style="color: #FFA500; margin: 0; font-size: 0.9rem; font-weight: 600;">
            📍 Vista Actual:
        </p>
        <p style="color: #ffffff; margin: 0.3rem 0 0 0; font-size: 0.85rem;">
            {estado_actual}
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown(
    """
    <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px;">
        <p style="color: #ffffff; margin: 0 0 0.5rem 0; font-weight: 600; font-size: 0.9rem;">📋 Enfoque:</p>
        <p style="color: #ffffff; margin: 0.3rem 0; font-size: 0.8rem;">✅ Logística, VRM-VA, Jurídico y Construcción</p>
        <p style="color: #ffffff; margin: 0.3rem 0; font-size: 0.8rem;">✅ Consolidación en Proyección Financiera</p>
        <p style="color: #ffffff; margin: 0.3rem 0; font-size: 0.8rem;">✅ Carga administrativa y valor total</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Almacén consolidado de totales; debe existir antes de renderizar cualquier módulo.
_init_pf_store()

if modulo_activo == "Inicio":
    render_inicio_proyecto()
    st.stop()

if modulo_activo == "VRM-VA":
    render_vrm_va_construccion()
    st.stop()

if modulo_activo == "Jurídico":
    render_juridico()
    st.stop()

if modulo_activo == "Construcción y Calificación":
    render_construccion()
    st.stop()

if modulo_activo == "Proyección Financiera":
    render_proyeccion_financiera()
    st.stop()

# st.sidebar.markdown(
#     """
#     <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px;">
#         <p style="color: #ffffff; margin: 0 0 0.5rem 0; font-weight: 600; font-size: 0.9rem;">📋 Funcionalidades:</p>
#         <p style="color: #ffffff; margin: 0.3rem 0; font-size: 0.8rem;">✅ Selección Multi-Ciudad</p>
#         <p style="color: #ffffff; margin: 0.3rem 0; font-size: 0.8rem;">✅ Cálculo Paramétrico</p>
#         <p style="color: #ffffff; margin: 0.3rem 0; font-size: 0.8rem;">✅ Reportes Exportables</p>
#         <p style="color: #ffffff; margin: 0.3rem 0; font-size: 0.8rem;">✅ Análisis Nacional</p>
#     </div>
#     """,
#     unsafe_allow_html=True
# )

# ==============================================================================
# VISTA 1: CONTEXTO Y EDA (OCULTA)
# ==============================================================================
# Sección comentada - No visible en la versión actual
_hidden_code = '''
if opcion == "1. Contexto y EDA":
    # Header principal con función reutilizable
    render_header("Análisis Exploratorio y Diagnóstico", "🔍")
    
    # Dashboard Summary - KPIs rápidos
    st.markdown("### 📊 Resumen Rápido del Proyecto")
    with st.container(border=True):
        sum_c1, sum_c2, sum_c3, sum_c4 = st.columns(4)
        sum_c1.metric("Ciudades Disponibles", "27", help="Número de ciudades con tarifario configurado")
        sum_c2.metric("Modelo Activo", "Paramétrico", help="Tipo de modelo utilizado para las predicciones")
        sum_c3.metric("Precisión", "~98%", help="Precisión estimada del modelo paramétrico")
        sum_c4.metric("Última Actualización", "Dic 2025", help="Fecha de última actualización del tarifario")
    
    st.markdown("""
    Este módulo explica **por qué fallaron los modelos tradicionales** (Regresión Lineal, XGBoost) y justifica el cambio hacia un modelo paramétrico.
    
    El hallazgo clave fue identificar que los costos no son lineales, sino que funcionan por **Tarifas Escalonadas (Step Functions)**.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("El Comportamiento Real (Escalonado)")
        # Simulación de datos para el gráfico
        x_sim = np.arange(1, 2500)
        y_sim = [5705 if x <= 1000 else (4909 if x <= 1500 else 4744) for x in x_sim]
        
        df_sim = pd.DataFrame({'Aspirantes': x_sim, 'Costo Unitario': y_sim})
        
        fig = px.line(df_sim, x='Aspirantes', y='Costo Unitario', 
                      title="Estructura de Tarifas (Cuadernillos)",
                      color_discrete_sequence=[ESAP_PALETTE['primary']])
        fig.update_layout(
            yaxis_title="Precio Unitario ($)",
            font=dict(family="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"),
            plot_bgcolor='#ffffff',
            paper_bgcolor=ESAP_PALETTE['neutral_light']
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Nota cómo el precio cae abruptamente en 1000 y 1500. Esto confunde a las regresiones lineales.")

    with col2:
        st.subheader("Distribución Geográfica")
        st.markdown("Los costos logísticos varían drásticamente según la ciudad. Un modelo que solo vea 'Aspirantes' ignorará la complejidad del terreno.")
        ciudades_ejemplo = pd.DataFrame({
            'Ciudad': ['Bogotá', 'Medellín', 'San Andrés', 'Quibdó'],
            'Costo Logístico Base': [45000, 85000, 250000, 180000]
        })
        fig2 = px.bar(ciudades_ejemplo, x='Ciudad', y='Costo Logístico Base', 
                      color='Costo Logístico Base',
                      title="Variabilidad de Costos Logísticos",
                      color_continuous_scale=[[0, ESAP_PALETTE['primary']], 
                                             [0.5, ESAP_PALETTE['secondary']], 
                                             [1, ESAP_PALETTE['accent']]])
        fig2.update_layout(
            font=dict(family="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"),
            plot_bgcolor='#ffffff',
            paper_bgcolor=ESAP_PALETTE['neutral_light']
        )
        st.plotly_chart(fig2, use_container_width=True)

# ==============================================================================
# VISTA 2: EVALUACIÓN DE MODELOS ML (OCULTA)
# ==============================================================================
# Sección comentada - No visible en la versión actual
# elif opcion == "2. Evaluación Modelos ML":
    # Header principal con función reutilizable
    render_header("Evaluación Visual de la Dificultad", "🧪")
    
    # Dashboard Summary para esta vista
    with st.container(border=True):
        st.markdown(
            """
            <div style="display: flex; gap: 1rem; flex-wrap: wrap; justify-content: center;">
                <span class="summary-badge badge-danger" style="background: rgba(220, 53, 69, 0.15); color: #dc3545;">❌ Regresión Lineal: R² = -1.50</span>
                <span class="summary-badge badge-danger" style="background: rgba(220, 53, 69, 0.15); color: #dc3545;">❌ XGBoost: R² = -0.94</span>
                <span class="summary-badge badge-success" style="background: rgba(40, 167, 69, 0.15); color: #28a745;">✅ Modelo Paramétrico: Recomendado</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("""
    Aquí visualizamos **por qué** el Machine Learning tradicional no es la herramienta adecuada para este problema específico.
    """)

    # --- GRÁFICA 1: EL ABISMO DEL OVERFITTING ---
    st.subheader("1. El 'Espejismo' del Entrenamiento")
    st.markdown("Mira la diferencia entre lo que el modelo 'cree' que sabe (Azul) y cómo le va en la realidad (Rojo).")

    # Datos preparados
    data_perf = pd.DataFrame({
        'Modelo': ['Gradient Boosting', 'XGBoost (Default)', 'Random Forest', 'Regresión Lineal'],
        'R2_Train': [0.99, 0.99, 0.80, 0.40],   # Entrenamiento (Casi perfecto en árboles)
        'R2_Test':  [-1.01, -0.94, -0.01, -1.50] # Realidad (Desastroso, peor que el promedio)
    })

    # Transformar para gráfica de barras agrupadas
    df_melt = data_perf.melt(id_vars=['Modelo'], var_name='Fase', value_name='Score R2')
    
    fig_overfit = px.bar(df_melt, x='Modelo', y='Score R2', color='Fase', barmode='group',
                         color_discrete_map={'R2_Train': ESAP_PALETTE['accent'], 
                                           'R2_Test': ESAP_PALETTE['primary']},
                         title="Comparativa: Ilusión (Train) vs. Realidad (Test)")
    
    fig_overfit.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Límite de Utilidad")
    fig_overfit.update_layout(
        font=dict(family="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"),
        plot_bgcolor='#ffffff',
        paper_bgcolor=ESAP_PALETTE['neutral_light']
    )
    st.plotly_chart(fig_overfit, use_container_width=True)
    
    st.error("""
    **Interpretación:** Las barras verdes (Entrenamiento) muestran modelos que "memorizaron" los datos. 
    Las barras rojas (Test) cayendo por debajo de 0 indican que los modelos fallaron estructuralmente al ver datos nuevos.
    """)

    st.markdown("---")

    # --- GRÁFICA 2: POR QUÉ FALLA LA REGRESIÓN (SIMULACIÓN) ---
    st.subheader("2. Anatomía del Error: Lineal vs. Escalonado")
    st.markdown("Esta gráfica simula por qué una línea recta (Regresión) no puede capturar el tarifario.")

    # Generar datos simulados de la curva real vs predicción lineal
    x_demo = np.linspace(0, 2000, 100)
    y_real = [5705 * x if x <= 1000 else (5705 * 1000 + 4909 * (x - 1000)) for x in x_demo]
    y_lineal = [5100 * x for x in x_demo] 

    df_demo = pd.DataFrame({
        'Aspirantes': x_demo,
        'Costo Real (Escalonado)': y_real,
        'Predicción Lineal (Errónea)': y_lineal
    })
    
    fig_error = px.line(df_demo, x='Aspirantes', y=['Costo Real (Escalonado)', 'Predicción Lineal (Errónea)'],
                        title="Simulación: Realidad vs. Modelo Lineal",
                        color_discrete_map={'Costo Real (Escalonado)': ESAP_PALETTE['primary'], 
                                          'Predicción Lineal (Errónea)': ESAP_PALETTE['accent']})
    fig_error.update_layout(
        font=dict(family="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"),
        plot_bgcolor='#ffffff',
        paper_bgcolor=ESAP_PALETTE['neutral_light']
    )
    st.plotly_chart(fig_error, use_container_width=True)
    
    st.info("""
    **El problema visual:** La línea roja (Predicción) ignora los cambios de tarifa. 
    * En 800 aspirantes, subestima el costo.
    * En 1200 aspirantes, lo sobreestima.
    **Solución:** Usar el modelo paramétrico (Calculadora) que sigue la línea azul exactamente.
    """)

# ==============================================================================
# VISTA 3: CALCULADORA DE COSTOS (OCULTA)
# ==============================================================================
# Sección comentada - No visible en la versión actual
# elif opcion == "3. Calculadora de Costos":
    # Header principal con función reutilizable
    render_header("Calculadora Paramétrica de Costos", "🧮")
    
    # Info box con descripción
    st.markdown(
        """
        <div class="custom-card">
            <p style="margin: 0; color: #333;">
                <strong>💡 Herramienta de precisión</strong> basada en <strong>Reglas de Negocio</strong> y <strong>Tarifario Maestro</strong>.
                Complete los parámetros a continuación para obtener una cotización detallada.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # --- FORMULARIO DE INGRESO ---
    with st.form("input_form"):
        st.subheader("📝 Parámetros del Concurso")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            aspirantes = st.number_input(
                "Número de Aspirantes", 
                min_value=1, 
                value=500, 
                step=10,
                help="Ingrese el número total de personas que presentarán la prueba. Mínimo 1 aspirante."
            )
        # NUEVO CONTROL DE FORMAS
        n_formas = st.number_input(
            "N° Tipos de Examen (Formas)", 
            min_value=1, 
            max_value=20, 
            value=1,
            help="Cantidad de versiones distintas del cuadernillo (Ej: Profesional, Técnico, Asistencial = 3 formas). Cada una requiere diseño independiente."
        )
        with col2:
            ciudad = st.selectbox(
                "Ciudad de Aplicación", 
                CIUDADES_DISPONIBLES,
                help="Seleccione la ciudad donde se realizará el concurso. Los costos varían según la ubicación geográfica."
            )
        with col3:
            prueba = st.radio(
                "Modalidad", 
                ["Escrita presencial - Material impreso", "Escrita presencial - Virtual en ambiente controlado"],
                help="Escrita presencial - Material impreso: requiere más jefes de salón. Escrita presencial - Virtual en ambiente controlado: menor personal pero mayor infraestructura tecnológica."
            )
            
            # Checkbox condicional: Solo aparece si es Virtual
            use_alquiler = False
            cantidad_equipos = 0
            
            if "Virtual" in prueba:
                use_alquiler = st.checkbox("¿Requiere Alquiler de PCs?", help="Active si necesita rentar equipos.")
                
                if use_alquiler:
                    st.markdown("---")
                    # Por defecto sugerimos n_aspirantes, pero el usuario puede bajarlo (ej. si hay turnos)
                    cantidad_equipos = st.number_input(
                        "💻 Cantidad de Equipos a Alquilar",
                        min_value=1,
                        max_value=aspirantes, # No puedes alquilar más que aspirantes (teóricamente)
                        value=aspirantes,     # Valor por defecto = 1:1
                        step=10,
                        help="Ingrese la cantidad base requerida. El sistema sumará automáticamente el 10% de backup."
                    )
                    
                    # Feedback visual inmediato para el usuario
                    if cantidad_equipos < aspirantes:
                        st.caption(f"ℹ️ Estás alquilando equipos para el **{cantidad_equipos/aspirantes:.0%}** de los aspirantes. (Asume {math.ceil(aspirantes/cantidad_equipos)} turnos).")

        submitted = st.form_submit_button("Calcular Cotización 🚀", type="primary", use_container_width=True)
    
    if submitted:
        # Ejecutar lógica con spinner
        with st.spinner('🔄 Calculando cotización... Por favor espere.'):
            res = calcular_modelo_parametrico(aspirantes, ciudad, prueba, use_alquiler, cantidad_equipos)
        
        st.divider()
        st.success('✅ Cotización calculada exitosamente!')
        
        st.subheader("🎯 Resultado de la Cotización")
        
        # --- VISUALIZACIÓN DEL INTERVALO (NUEVO) ---
        col_rango_1, col_rango_2, col_rango_3 = st.columns([1, 2, 1])
        
        with col_rango_1:
            st.metric(
                label="Escenario Optimista (Mínimo)",
                value=f"${res['intervalo']['min']:,.0f}",
                help="Asume transporte sin contratiempos y cero desperdicio."
            )
            
        with col_rango_2:
            # Valor Central Grande
            st.markdown(f"""
            <div style="text-align: center;">
                <span style="font-size: 1.2em; color: gray;">Estimación Central</span><br>
                <span style="font-size: 2.5em; font-weight: bold; color: #2E86C1;">${res['financiero']['TOTAL_BASE']:,.0f}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Barra de progreso visual del rango
            rango_pct = 100 * (res['financiero']['TOTAL_BASE'] - res['intervalo']['min']) / res['intervalo']['gap']
            st.progress(int(rango_pct))
            st.caption(f"Rango de Riesgo: +/- ${res['intervalo']['gap']/2:,.0f} (Debido a volatilidad logística)")

        with col_rango_3:
            st.metric(
                label="Escenario Conservador (Máximo)",
                value=f"${res['intervalo']['max']:,.0f}",
                delta=f"Reserve hasta: ${res['unitario_max']:,.0f}/asp",
                delta_color="inverse",
                help="Incluye +20% en transporte y +5% en imprevistos generales."
            )

        st.divider()
        
        # --- KPIS LOGÍSTICOS ---
        st.markdown("#### 📦 Recursos Logísticos Requeridos")
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🏢 Sitios", res['logistica']['Sitios'], help="Número de sedes necesarias (500 aspirantes por sitio)")
            c2.metric("🚪 Salones", res['logistica']['Salones'], help="Número de salones requeridos (25 aspirantes por salón)")
            total_personas = sum([item['Cantidad'] for item in res['detalle_nomina']])
            c3.metric("👥 Total Staff", total_personas, help="Personal total requerido para la operación")
            costo_impresion_viz = res['financiero']['Material Examen Aplicación'] / aspirantes
            c4.metric("🖨️ Tarifa Impresión", f"${costo_impresion_viz:,.0f}/u", help="Costo por cuadernillo según volumen")
        
        # --- PESTAÑAS PARA EL DETALLE ---
        tab1, tab2 = st.tabs(["👥 Nómina Detallada", "📊 Análisis de Costos"])
        
        with tab1:
            df_personal = pd.DataFrame(res['detalle_nomina'])
            st.dataframe(
                df_personal.style.format({'Tarifa': '${:,.0f}', 'Subtotal': '${:,.0f}'}),
                use_container_width=True, hide_index=True
            )
            
        with tab2:
            # Calcular totales y porcentajes para la tabla
            total_costos = res['financiero']['TOTAL_BASE']
            
            # --- VISUALIZACIÓN COMPUESTA (PIE + BAR) ---
            # 1. Usar constante global para claves de materiales
            costo_materiales_ops = sum(res['financiero'].get(k, 0) for k in KEYS_MATERIALES)
            
            df_main = pd.DataFrame([
                {'Rubro': 'Transporte', 'Costo': res['financiero'].get('Transporte y Distribución', 0)},
                {'Rubro': 'Nómina', 'Costo': res['financiero'].get('Personal Logístico', 0)},
                {'Rubro': 'Kits de Aseo', 'Costo': res['financiero'].get('Kit de Aseo', 0) + res['financiero'].get('Kit para Baños', 0)},
                {'Rubro': 'Tecnología', 'Costo': res['financiero'].get('Tecnología (Alquiler PC)', 0)},
                {'Rubro': 'Materiales Operativos', 'Costo': costo_materiales_ops}
            ])
            
            # 2. Preparar datos Detalle (Bar) - solo materiales
                df_details = pd.DataFrame([
                    {'Item': k, 'Costo': res['financiero'].get(k, 0)} for k in KEYS_MATERIALES if res['financiero'].get(k, 0) > 0
                ]).sort_values('Costo', ascending=True)

            # 3. Crear Subplots
            fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'xy'}]],
                                subplot_titles=("Distribución General", "Detalle Materiales Ops"))

            # Trace 1: Pie Central
            fig.add_trace(go.Pie(labels=df_main['Rubro'], values=df_main['Costo'], hole=0.4,
                                 marker_colors=['#003366', '#0066CC', '#FFB347', '#FF8C00', '#28a745', '#6c757d']), row=1, col=1)

            # Trace 2: Bar Breakdown
            fig.add_trace(go.Bar(x=df_details['Costo'], y=df_details['Item'], orientation='h',
                                 marker_color='#FF8C00'), row=1, col=2)

            fig.update_layout(showlegend=False, 
                              font=dict(family="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"),
                              paper_bgcolor=ESAP_PALETTE['neutral_light'])
            
            # Layout Vertical: Tabla primero, luego Gráfico
            st.markdown("##### 📋 Resumen")
            df_main['Porcentaje'] = (df_main['Costo'] / total_costos * 100).round(1)
            st.dataframe(df_main.style.format({'Costo': '${:,.0f}'}), hide_index=True, use_container_width=True)
            
            st.markdown("##### 📊 Distribución Visual")
            st.plotly_chart(fig, use_container_width=True)
            
            # Alerta sobre transporte
            if res['financiero'].get('Transporte y Distribución', 0) > res['financiero']['TOTAL_BASE'] * 0.3:
                st.warning(f"⚠️ **Atención:** El transporte representa una parte muy alta del presupuesto. La variabilidad en el precio de la gasolina o fletes en {ciudad} podría afectar significativamente el margen.")

'''
# Fin de secciones ocultas

# ==============================================================================
# VISTA PRINCIPAL: COTIZACIÓN MULTI-CIUDAD
# ==============================================================================
# Header principal con función reutilizable
render_header("Simulador de Recursos Nacional", "🌎")

# Info card con instrucciones
st.markdown(
    """
    <div class="custom-card">
        <p style="margin: 0; color: #333;">
            <strong>🗺️ Cotizador Nacional Integrado:</strong> Seleccione las ciudades objetivo y defina el volumen de aspirantes por sede. La herramienta se encargará de unificar los costos de diseño y sumar la logística individual de cada ciudad para generar un reporte financiero consolidado.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Equipo base al inicio del módulo; su costo se suma al total de Logística.
costo_equipo_log = render_equipo_base("log")
st.divider()

# 1. Selección de Ciudades (usa constante global)
ciudades_sel = st.multiselect(
    "🏙️ Seleccione las Ciudades del Operativo:", 
    CIUDADES_DISPONIBLES, 
    default=["Bogotá", "Medellín"],
    help="Puede seleccionar múltiples ciudades. Los costos se calcularán individualmente y se sumarán para el total nacional."
)

if ciudades_sel:
    # 2. Configuración Global de Modalidad
    st.subheader("⚙️ Configuración del Operativo")
    
    col_global_1, col_global_2, col_global_3 = st.columns(3)
    with col_global_1:
        modalidad_global = st.radio(
            "Modalidad General", 
            ["Escrita presencial - Material impreso", "Escrita presencial - Virtual en ambiente controlado"],
            horizontal=False,
            help="La modalidad aplica para todas las ciudades seleccionadas. Escrita requiere más personal, Virtual requiere más tecnología."
        )
    
    with col_global_2:
        formas_global = st.number_input(
            "📝 Formas de Prueba",
            min_value=1,
            max_value=20,
            value=1,
            step=1,
            help="Cantidad de versiones diferentes del examen (ej: Forma A, B, C). Aplica a todas las ciudades. Afecta costos de diagramación."
        )
        if formas_global > 1:
            st.caption(f"Se aplicarán {formas_global} versiones del examen en todas las ciudades.")
    
    # 3. Configuración de Aspirantes (Data Editor)
    st.subheader("📋 Asignación de Aspirantes por Ciudad")
    
    # Detectar si es virtual para habilitar opcion de equipos
    es_virtual = "Virtual" in modalidad_global
    
    # Datos base
    data_base = {
        'Ciudad': ciudades_sel,
        'Aspirantes': [500] * len(ciudades_sel),
    }

    # Si es virtual, agregamos columna de equipos (default 1:1)
    if es_virtual:
        data_base['Equipos'] = [500] * len(ciudades_sel)

    # Crear DF inicial
    df_input = pd.DataFrame(data_base)

    st.caption("ℹ️ Población en situación de discapacidad: se calcula automáticamente como el "
               "**7% del total de aspirantes** (no requiere digitarse).")

    # Configuración de columnas base
    col_config = {
        "Aspirantes": st.column_config.NumberColumn(
            "Digite el número de aspirantes",
            min_value=1,
            max_value=100000,
            step=10,
        ),
    }

    # Configuración condicional para equipos
    if es_virtual:
        col_config["Equipos"] = st.column_config.NumberColumn(
            "Equipos de Cómputo",
            min_value=0,
            max_value=100000,
            step=1,
            help="Cantidad de computadores a alquilar"
        )

    # Editor — key estable por selección de ciudades para no perder los valores al escribir.
    editor_key = f"log_editor_{'-'.join(ciudades_sel)}_{es_virtual}"
    edited_df = st.data_editor(
        df_input,
        column_config=col_config,
        hide_index=True,
        use_container_width=True,
        key=editor_key,
    )
    
    if st.button("Calcular Cotización Global 🚀", type="primary"):
        
        resultados_lista = []
        total_global = 0
        total_min_global = 0
        total_max_global = 0
        total_aspirantes = 0
        
        # Barra de progreso
        progress_text = "Calculando costos por ciudad..."
        my_bar = st.progress(0, text=progress_text)
        
        for idx, row in enumerate(edited_df.itertuples()):
            ciudad_iter = row.Ciudad
            asp_iter = row.Aspirantes
            # Población en situación de discapacidad: 7% de los aspirantes de la ciudad.
            discap_iter = round(asp_iter * 0.07)
            equipos_iter = getattr(row, 'Equipos', 0) if es_virtual else 0
            
            # Usar modalidad global
            mod_iter = modalidad_global
            
            # Determinamos parámetros de alquiler para esta ciudad
            # Si es virtual, asumimos que requiere alquiler si equipos > 0
            req_alquiler = es_virtual and (equipos_iter > 0)
            
            # Calcular usando la función existente
            # calcular_modelo_parametrico(n_aspirantes, ciudad, tipo_prueba, requiere_alquiler, n_equipos_alquiler, n_formas)
            res = calcular_modelo_parametrico(asp_iter, ciudad_iter, mod_iter, requiere_alquiler=req_alquiler, n_equipos_alquiler=equipos_iter, n_formas=formas_global)
            
            # Acumular
            costo_base = res['financiero']['TOTAL_BASE']
            total_global += costo_base
            total_min_global += res['intervalo']['min']
            total_max_global += res['intervalo']['max']
            total_aspirantes += asp_iter
            
            resultados_lista.append({
                'Ciudad': ciudad_iter,
                'Aspirantes': asp_iter,
                'Formas': formas_global,
                'Discapacitados': discap_iter,
                'Equipos': equipos_iter,
                'Modalidad': mod_iter,
                'Costo Total': costo_base,
                'Costo Unitario': res['unitario'],
                'Sitios': res['logistica']['Sitios'],
                'Salones': res['logistica']['Salones'],
                'Staff': sum(x['Cantidad'] for x in res['detalle_nomina']),
                'full_res': res # Guardar resultado completo para evitar recálculos
            })
            
        # Actualizar barra
            my_bar.progress((idx + 1) / len(edited_df), text=progress_text)
            
        my_bar.empty()
        
        # --- GUARDAR EN SESSION STATE ---
        st.session_state['mc_resultados'] = resultados_lista
        st.session_state['mc_total'] = total_global
        st.session_state['mc_total_min'] = total_min_global
        st.session_state['mc_total_max'] = total_max_global
        pf_registrar("Logística", total_min_global + costo_equipo_log, total_max_global + costo_equipo_log)
        # Comparte el total de aspirantes como inscritos base para los demás módulos.
        st.session_state['global_inscritos'] = total_aspirantes
        st.session_state['mc_aspirantes'] = total_aspirantes
        st.session_state['mc_es_virtual'] = es_virtual # Guardar contexto
        st.session_state['mc_modalidad'] = modalidad_global # Guardar modalidad
        st.session_state['mc_formas'] = formas_global # Guardar formas de prueba
        
    # --- RENDERIZADO PERSISTENTE ---
    if 'mc_resultados' in st.session_state:
        # Recuperar datos
        resultados_lista = st.session_state['mc_resultados']
        total_global = st.session_state['mc_total']
        total_min_global = st.session_state['mc_total_min']
        total_max_global = st.session_state['mc_total_max']
        pf_registrar("Logística", total_min_global + costo_equipo_log, total_max_global + costo_equipo_log)
        total_aspirantes = st.session_state['mc_aspirantes']
        # Usar variable guardada o actual si coincide lógica, pero mejor usar la guardada para consistencia
        # Sin embargo, 'es_virtual' viene del input actual. Si el usuario cambia inputs pero no recalcula, puede haber mismatch.
        # Asumiremos que si hay resultados, mostramos esos resultados.
        
        st.divider()
        
        # --- RESULTADOS GLOBALES ---
        st.subheader("💰 Resumen Financiero Nacional")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.metric("Costo Total Operativo", f"${total_global:,.0f}")
        with c2:
            st.metric("Total Aspirantes", f"{total_aspirantes:,.0f}")
        with c3:
            if total_aspirantes > 0:
                promedio_unitario = total_global / total_aspirantes
                st.metric("Costo Promedio / Aspirante", f"${promedio_unitario:,.0f}")

        total_discapacitados = round(total_aspirantes * 0.07)
        st.metric("Población en situación de discapacidad (7%)", f"{total_discapacitados:,.0f}")
        st.caption("Calculado como el 7% del total de aspirantes.")

        st.caption("**Fuente:** ESTUDIO DE MERCADO - CONCURSO MERITOS, ESAP 2025 (por actualizar)")

        if costo_equipo_log > 0:
            st.metric("Costo total del módulo (con equipo base)", f"${total_global + costo_equipo_log:,.0f}")

        render_boton_borrar_modulo(
            "Logística",
            ["mc_resultados", "mc_total", "mc_total_min", "mc_total_max", "mc_aspirantes",
             "mc_es_virtual", "mc_modalidad", "mc_formas", "log_equipo_df", "log_equipo_editor"],
        )

        # --- KPIs ESPECÍFICOS VIRTUAL ---
        if st.session_state.get('mc_es_virtual', False):
            st.divider()
            st.markdown("#### 💻 Indicadores de Infraestructura Tecnológica")
            
            kv1, kv2, kv3 = st.columns(3)
            
            # Calcular totales
            total_equipos_pc = sum(r.get('Equipos', 0) for r in resultados_lista)
            # FIX: Usar .get() y la nueva clave 'Tecnología (Alquiler PC)' o 'Tecnología' si existiera
            total_costo_tech = sum(r['full_res']['financiero'].get('Tecnología (Alquiler PC)', 0) for r in resultados_lista)
            
            with kv1:
                st.metric("Total Equipos a Alquilar", f"{total_equipos_pc:,.0f}")
            with kv2:
                st.metric("Costo Tecnología", f"${total_costo_tech:,.0f}")
            with kv3:
                if total_aspirantes > 0 and total_equipos_pc > 0:
                    ratio_pc = total_equipos_pc / total_aspirantes
                    st.metric("Ratio Equipos/Aspirante", f"{ratio_pc:.2f}")
        
        # --- INTERVALO DE CONFIANZA ---
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(90deg, rgba(0,123,255,0.1) 0%, rgba(40,167,69,0.1) 100%);
                border-left: 4px solid #007bff;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <h4 style="margin: 0; color: #007bff; font-size: 16px;">
                    💡 Rango de Presupuesto Sugerido
                </h4>
                <p style="margin: 8px 0 0 0; font-size: 14px; color: #333;">
                    Entre <strong style="color: #28a745;">${total_min_global:,.0f}</strong> (Optimista) 
                    y <strong style="color: #dc3545;">${total_max_global:,.0f}</strong> (Conservador)
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # --- DETALLE POR CIUDAD ---
        st.subheader("📍 Desglose por Ciudad")
        df_res = pd.DataFrame(resultados_lista)
        if 'full_res' in df_res.columns:
            df_res_view = df_res.drop(columns=['full_res'])
        else:
            df_res_view = df_res
        
        # Formato condicional para resaltar costos altos
        st.dataframe(
            df_res_view.style.format({
                'Costo Total': '${:,.0f}',
                'Costo Unitario': '${:,.0f}',
                'Aspirantes': '{:,.0f}',
                'Formas': '{:,.0f}',
                'Discapacitados': '{:,.0f}',
                'Equipos': '{:,.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # --- DESCARGA ---
        st.markdown("#### 📥 Exportar Resultados")
        col_download1, col_download2 = st.columns(2)
        
        with col_download1:
            # Convertir a CSV para descargar
            csv = df_res_view.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name='cotizacion_nacional_esap.csv',
                mime='text/csv',
                use_container_width=True,
                help="Descarga el detalle en formato CSV para Excel"
            )
        
        with col_download2:
            # Generar reporte HTML Profesional
            
            # 1. Estilos CSS
            estilos_css = """
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; margin: 0; padding: 0; }
                .header { background: linear-gradient(135deg, #003366 0%, #004080 100%); color: white; padding: 40px 20px; text-align: center; border-bottom: 5px solid #FF8C00; }
                .header h1 { margin: 0; font-size: 28px; text-transform: uppercase; letter-spacing: 2px; }
                .header p { margin: 10px 0 0 0; font-size: 16px; opacity: 0.9; }
                .container { max-width: 1000px; margin: 40px auto; padding: 0 20px; }
                .section-title { color: #003366; border-bottom: 2px solid #FF8C00; padding-bottom: 10px; margin-top: 40px; margin-bottom: 20px; font-weight: bold; font-size: 20px; }
                
                /* Tablas */
                table { width: 100%; border-collapse: collapse; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }
                th { background-color: #003366; color: white; padding: 15px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 14px; }
                td { padding: 12px 15px; border-bottom: 1px solid #eee; font-size: 14px; }
                tr:nth-child(even) { background-color: #f8f9fa; }
                tr:hover { background-color: #f1f1f1; }
                
                /* Summary Box */
                .summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
                .kpi-card { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 5px solid #003366; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
                .kpi-label { font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: 1px; }
                .kpi-value { font-size: 24px; font-weight: bold; color: #003366; margin-top: 5px; }
                
                /* Rangos */
                .range-box { padding: 15px; border-radius: 8px; margin-top: 20px; background: linear-gradient(to right, rgba(40,167,69,0.1), rgba(220,53,69,0.1)); border: 1px solid #ddd; text-align: center; }
                .range-title { font-weight: bold; color: #333; margin-bottom: 10px; }
                .range-values { font-size: 18px; }
                .val-min { color: #28a745; font-weight: bold; }
                .val-max { color: #dc3545; font-weight: bold; }
                
                .footer { text-align: center; margin-top: 50px; padding: 20px; font-size: 12px; color: #999; border-top: 1px solid #eee; }
            </style>
            """
            
            # 2. Construcción del HTML
            
            # A. Tabla Resumen General
            html_rows = ""
            for _, row in df_res.iterrows():
                # Usar valor guardado en row si posible, o fallback
                equipos_val = f"{row.get('Equipos', 0):,.0f}" if st.session_state.get('mc_es_virtual', False) else "N/A"
                html_rows += f"""
                <tr>
                    <td style="font-weight: bold;">{row['Ciudad']}</td>
                    <td>{row['Aspirantes']:,.0f}</td>
                    <td>{row['Discapacitados']:,.0f}</td>
                    <td>{equipos_val}</td>
                    <td>${row['Costo Unitario']:,.0f}</td>
                    <td style="font-weight: bold; color: #003366;">${row['Costo Total']:,.0f}</td>
                </tr>
                """

            # B. Bloques Detallados por Ciudad
            html_detalles = ""
            for item in resultados_lista:
                res_c = item['full_res']
                nombre_c = item['Ciudad']
                total_c = res_c['financiero']['TOTAL_BASE']
                
                # KPIs Logísticos
                sitios_c = res_c['logistica']['Sitios']
                salones_c = res_c['logistica']['Salones']
                staff_c = sum([x['Cantidad'] for x in res_c['detalle_nomina']])
                # Evitar div por cero si aspirantes es 0 (raro pero posible)
                asp_c = item['Aspirantes'] if item['Aspirantes'] > 0 else 1
                
                # CORRECCIÓN: Usar clave nueva para "Impresión" (Material Examen Aplicación)
                # Antes: '1. Impresión Variable' -> Ahora: 'Material Examen Aplicación'
                imp_unit_c = res_c['financiero'].get('Material Examen Aplicación', 0) / asp_c
                
                # Tabla Financiera
                # Recalcular costo materiales (suma de claves específicas de materiales en 'financiero' o usar 'Materiales' si existiera, 
                # pero la nueva estructura pone todo en 'financiero')
                
                # Usar constante global para claves de materiales
                costo_mat_c = sum(res_c['financiero'].get(k, 0) for k in KEYS_MATERIALES)

                rows_fin = [
                    ('Transporte', res_c['financiero'].get('Transporte y Distribución', 0)),
                    ('Nómina', res_c['financiero'].get('Personal Logístico', 0)),
                    ('Tecnología', res_c['financiero'].get('Tecnología (Alquiler PC)', 0)),
                    ('Materiales', costo_mat_c),
                    ('Aseo y Limpieza', res_c['financiero'].get('Kit de Aseo', 0) + res_c['financiero'].get('Kit para Baños', 0)),
                    # Disposición Final ya está en materiales en este nuevo esquema, o lo separamos si se prefiere
                    # La dejaremos en materiales para simplificar la tabla resumen
                ]
                
                html_rows_fin = ""
                for concepto, valor in rows_fin:
                    if valor > 0:
                        pct = (valor / total_c) * 100
                        html_rows_fin += f"<tr><td>{concepto}</td><td>${valor:,.0f}</td><td>{pct:.1f}%</td></tr>"
                
                html_detalles += f"""
                <div style="margin-bottom: 30px; border: 1px solid #ddd; padding: 20px; border-radius: 8px; background: white;">
                    <div style="border-bottom: 2px solid #ddd; margin-bottom: 15px; padding-bottom: 10px;">
                        <span style="font-size: 18px; font-weight: bold; color: #003366;">{nombre_c}</span>
                        <span style="float: right; font-weight: bold; color: #28a745; font-size: 18px;">Total: ${total_c:,.0f}</span>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                        <div style="text-align: center;"><div style="font-size: 12px; color: #666;">SITIOS</div><div style="font-weight: bold; font-size: 16px;">{sitios_c}</div></div>
                        <div style="text-align: center;"><div style="font-size: 12px; color: #666;">SALONES</div><div style="font-weight: bold; font-size: 16px;">{salones_c}</div></div>
                        <div style="text-align: center;"><div style="font-size: 12px; color: #666;">STAFF</div><div style="font-weight: bold; font-size: 16px;">{staff_c}</div></div>
                        <div style="text-align: center;"><div style="font-size: 12px; color: #666;">TARIFA IMP.</div><div style="font-weight: bold; font-size: 16px;">${imp_unit_c:,.0f}</div></div>
                    </div>
                    
                    <table style="width: 100%; font-size: 13px;">
                        <thead style="background: #eee;">
                            <tr><th style="padding: 8px; background: #eee; color: #333;">Concepto</th><th style="padding: 8px; background: #eee; color: #333;">Costo</th><th style="padding: 8px; background: #eee; color: #333;">%</th></tr>
                        </thead>
                        <tbody>
                            {html_rows_fin}
                        </tbody>
                    </table>
                </div>
                """
            
            # C. Tabla de Nómina Consolidada para HTML
            nomina_html_dict = {}
            for item in resultados_lista:
                res_temp = item['full_res']
                for cargo in res_temp['detalle_nomina']:
                    nombre_cargo = cargo['Cargo']
                    if nombre_cargo not in nomina_html_dict:
                        nomina_html_dict[nombre_cargo] = {'Cantidad': 0, 'Subtotal': 0, 'Tarifa': cargo['Tarifa']}
                    nomina_html_dict[nombre_cargo]['Cantidad'] += cargo['Cantidad']
                    nomina_html_dict[nombre_cargo]['Subtotal'] += cargo['Subtotal']
            
            html_nomina_rows = ""
            total_nomina_html = 0
            for cargo, data in nomina_html_dict.items():
                html_nomina_rows += f"<tr><td>{cargo}</td><td>{data['Cantidad']:,}</td><td>${data['Tarifa']:,.0f}</td><td style='font-weight: bold;'>${data['Subtotal']:,.0f}</td></tr>"
                total_nomina_html += data['Subtotal']
            
            html_nomina_consolidada = f"""
            <table>
                <thead>
                    <tr><th>Cargo</th><th>Cantidad</th><th>Tarifa Unitaria</th><th>Subtotal</th></tr>
                </thead>
                <tbody>
                    {html_nomina_rows}
                    <tr style="background: #003366; color: white; font-weight: bold;">
                        <td colspan="3">TOTAL NÓMINA</td>
                        <td>${total_nomina_html:,.0f}</td>
                    </tr>
                </tbody>
            </table>
            """
            
            # D. Tabla de Recursos Consolidados para HTML
            recursos_html_dict = {
                "Empaque": {"cost_key": "Empaque", "qty_type": "aspirantes", "val": 0, "cost": 0},
                "Kit Dactiloscopista": {"cost_key": "Kit Dactiloscopista", "qty_type": "calc_dactilo", "val": 0, "cost": 0},
                "Kit de Aplicación": {"cost_key": "Kit de Aplicación", "qty_type": "salones", "val": 0, "cost": 0},
                "Kit de Aseo": {"cost_key": "Kit de Aseo", "qty_type": "calc_aseo", "val": 0, "cost": 0},
                "Kit para Baños": {"cost_key": "Kit para Baños", "qty_type": "calc_aseo", "val": 0, "cost": 0},
                "Lectura y Procesamiento": {"cost_key": "Lectura y Procesamiento", "qty_type": "aspirantes", "val": 0, "cost": 0},
                "Material Examen Aplicación": {"cost_key": "Material Examen Aplicación", "qty_type": "aspirantes", "val": 0, "cost": 0},
                "Material Examen Exhibición": {"cost_key": "Material Examen Exhibición", "qty_type": "aspirantes", "val": 0, "cost": 0},
                "Material Aplicación (Papelería)": {"cost_key": "Material Aplicación (Papelería)", "qty_type": "salones", "val": 0, "cost": 0},
                "Infraestructura (Diagramación)": {"cost_key": "Infraestructura (Diagramación)", "qty_type": "formas", "val": 0, "cost": 0},
                "Transporte y Distribución": {"cost_key": "Transporte y Distribución", "qty_type": "aspirantes", "val": 0, "cost": 0},
                "Tecnología (Alquiler PC)": {"cost_key": "Tecnología (Alquiler PC)", "qty_type": "equipos", "val": 0, "cost": 0},
                "Disposición Final": {"cost_key": "Disposición Final", "qty_type": "aspirantes", "val": 0, "cost": 0},
            }
            
            for item in resultados_lista:
                res = item['full_res']
                fin = res['financiero']
                log = res['logistica']
                asp_c = item['Aspirantes']
                salones_c = log['Salones']
                equipos_c = item.get('Equipos', 0)
                
                q_dactilo_c = math.ceil(salones_c / 4)
                q_aseo_c = math.ceil(salones_c / 6)
                
                for nombre_item, data in recursos_html_dict.items():
                    ckey = data['cost_key']
                    costo_item = fin.get(ckey, 0)
                    data['cost'] += costo_item
                    
                    qtype = data['qty_type']
                    if qtype == "aspirantes":
                        data['val'] += asp_c
                    elif qtype == "salones":
                        data['val'] += salones_c
                    elif qtype == "calc_dactilo":
                        data['val'] += q_dactilo_c
                    elif qtype == "calc_aseo":
                        data['val'] += q_aseo_c
                    elif qtype == "equipos":
                        data['val'] += equipos_c
                    elif qtype == "formas":
                        data['val'] = st.session_state.get('mc_formas', 1)  # Es global, no se suma
            
            html_recursos_rows = ""
            total_recursos_html = 0
            for concepto, data in recursos_html_dict.items():
                if data['cost'] > 0:
                    html_recursos_rows += f"<tr><td>{concepto}</td><td>{data['val']:,}</td><td style='font-weight: bold;'>${data['cost']:,.0f}</td></tr>"
                    total_recursos_html += data['cost']
            
            html_recursos_consolidados = f"""
            <table>
                <thead>
                    <tr><th>Concepto</th><th>Cantidad</th><th>Costo Total</th></tr>
                </thead>
                <tbody>
                    {html_recursos_rows}
                    <tr style="background: #003366; color: white; font-weight: bold;">
                        <td colspan="2">TOTAL RECURSOS</td>
                        <td>${total_recursos_html:,.0f}</td>
                    </tr>
                </tbody>
            </table>
            """
            
            reporte_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Reporte de Costeo ESAP</title>
                {estilos_css}
            </head>
            <body>
                <div class="header">
                    <h1>Reporte de Cotización Nacional</h1>
                    <p>ESAP - Simulador de Costos de Concursos</p>
                </div>
                
                <div class="container">
                    <!-- CONFIGURACIÓN DEL OPERATIVO -->
                    <div class="section-title">⚙️ Configuración del Operativo</div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; border-left: 5px solid #FF8C00;">
                        <table style="width: 100%; box-shadow: none; margin: 0;">
                            <tr>
                                <td style="border: none; padding: 10px;"><strong>Modalidad:</strong></td>
                                <td style="border: none; padding: 10px;">{st.session_state.get('mc_modalidad', 'No especificada')}</td>
                            </tr>
                            <tr>
                                <td style="border: none; padding: 10px;"><strong>Formas de Prueba:</strong></td>
                                <td style="border: none; padding: 10px;">{st.session_state.get('mc_formas', 1)}</td>
                            </tr>
                            <tr>
                                <td style="border: none; padding: 10px;"><strong>Ciudades:</strong></td>
                                <td style="border: none; padding: 10px;">{len(resultados_lista)}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <!-- RESUMEN EJECUTIVO -->
                    <div class="section-title">📊 Resumen Ejecutivo</div>
                    
                    <div class="summary-grid">
                        <div class="kpi-card">
                            <div class="kpi-label">Costo Total Operativo</div>
                            <div class="kpi-value">${total_global:,.0f}</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Total Aspirantes</div>
                            <div class="kpi-value">{total_aspirantes:,.0f}</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Promedio por Aspirante</div>
                            <div class="kpi-value">${total_global/total_aspirantes:,.0f}</div>
                        </div>
                    </div>

                    <div class="range-box">
                        <div class="range-title">💡 Rango Presupuestal Sugerido</div>
                        <div class="range-values">
                            <span class="val-min">${total_min_global:,.0f} (Optimista)</span>
                            &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
                            <span class="val-max">${total_max_global:,.0f} (Conservador)</span>
                        </div>
                    </div>
                    
                    <!-- RESUMEN POR CIUDAD -->
                    <div class="section-title">📍 Resumen por Ciudad</div>
                    <table>
                        <thead>
                            <tr>
                                <th>Ciudad</th>
                                <th>Aspirantes</th>
                                <th>Discapacitados</th>
                                <th>Equipos PC</th>
                                <th>Cost. Unitario</th>
                                <th>Cost. Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {html_rows}
                        </tbody>
                    </table>
                    
                    <!-- NÓMINA CONSOLIDADA -->
                    <div class="section-title">👥 Personal Logístico Consolidado</div>
                    {html_nomina_consolidada}
                    
                    <!-- RECURSOS E INSUMOS -->
                    <div class="section-title">📦 Consolidado de Recursos e Insumos</div>
                    {html_recursos_consolidados}
                    
                    <!-- DETALLE POR CIUDAD -->
                    <div class="section-title">🏙️ Análisis Detallado por Ciudad</div>
                    {html_detalles}
                    
                    <div class="footer">
                        Generado automáticamente por el Simulador de Costos ESAP<br>
                        Fecha: {pd.Timestamp.now().strftime('%d de %B de %Y')}
                    </div>
                </div>
            </body>
            </html>
            """

            st.download_button(
                label="📄 Descargar Reporte (HTML)",
                data=reporte_html.encode('utf-8'),
                file_name='reporte_cotizacion_esap.html',
                mime='text/html',
                use_container_width=True,
                help="Descarga un reporte profesional en formato HTML"
            )

        st.divider()

        # --- PESTAÑAS PARA EL DETALLE GLOBAL ---
        # Indicador de navegación para el usuario
        st.markdown("""
            <div class="tab-navigation-hint">
                💡 <strong>Navegación:</strong> Use las pestañas a continuación para explorar diferentes vistas del presupuesto.
                <br>📦 <em>Consolidado</em> → Vista general de recursos | 
                👥 <em>Nómina</em> → Detalle del personal | 
                📊 <em>Análisis</em> → Gráficos y distribución de costos
            </div>
        """, unsafe_allow_html=True)
        
        tab_consolidado, tab_nomina, tab_analisis = st.tabs([
            "📦 1. Consolidado de Recursos", 
            "👥 2. Nómina Detallada Global", 
            "📊 3. Análisis de Costos Global"
        ])

        with tab_consolidado:
            st.markdown("### 📦 Consolidado de Recursos e Insumos")
            st.info("📋 **Vista actual:** Resumen totalizado de cantidades y costos para la operación nacional.")
            
            # Obtener formas de prueba y modalidad desde session_state
            n_formas_cons = st.session_state.get('mc_formas', 1)
            es_virtual_cons = st.session_state.get('mc_es_virtual', False)
            
            # Mapeo de Campos Solicitados
            # Definimos los items y su lógica de cantidad
            # qty_type: aspirantes, salones, staff, calc_dactilo, calc_aseo, aspirantes_x_formas, equipos
            
            # Items base (comunes a ambas modalidades)
            items_consolidado = {
                "Empaque": {"cost_key": "Empaque", "qty_type": "aspirantes", "val": 0, "cost": 0},
                "Kit Dactiloscopista": {"cost_key": "Kit Dactiloscopista", "qty_type": "calc_dactilo", "val": 0, "cost": 0},
                "Kit de aplicación": {"cost_key": "Kit de Aplicación", "qty_type": "salones", "val": 0, "cost": 0},
                "Kit de aseo": {"cost_key": "Kit de Aseo", "qty_type": "calc_aseo", "val": 0, "cost": 0},
                "Kit para baños": {"cost_key": "Kit para Baños", "qty_type": "calc_aseo", "val": 0, "cost": 0},
                "Lectura": {"cost_key": "Lectura y Procesamiento", "qty_type": "aspirantes", "val": 0, "cost": 0},
                "Material exhibición": {"cost_key": "Material Examen Exhibición", "qty_type": "aspirantes", "val": 0, "cost": 0},
                "Material aplicación": {"cost_key": "Material Aplicación (Papelería)", "qty_type": "salones", "val": 0, "cost": 0},
                "Personal logístico": {"cost_key": "Personal Logístico", "qty_type": "staff", "val": 0, "cost": 0},
            }
            
            # Items específicos según modalidad
            if es_virtual_cons:
                # Modalidad Virtual: Fusionar materiales examen en "Uso de plataforma FastTest" y cambiar Transporte por Equipo de computo
                items_consolidado["Uso de plataforma FastTest"] = {"cost_key": ["Material Examen Aplicación", "Material Examen Exhibición"], "qty_type": "aspirantes", "val": 0, "cost": 0}
                items_consolidado["Equipo de computo"] = {"cost_key": "Tecnología (Alquiler PC)", "qty_type": "equipos", "val": 0, "cost": 0}
            else:
                # Modalidad Impresa: Items separados
                items_consolidado["Material examen aplicación"] = {"cost_key": "Material Examen Aplicación", "qty_type": "aspirantes_x_formas", "val": 0, "cost": 0}
                items_consolidado["Material examen exhibición"] = {"cost_key": "Material Examen Exhibición", "qty_type": "aspirantes", "val": 0, "cost": 0}
                items_consolidado["Transporte"] = {"cost_key": "Transporte y Distribución", "qty_type": "aspirantes", "val": 0, "cost": 0}
            
            # Iterar sobre las ciudades y acumular
            for item in resultados_lista:
                res = item['full_res']
                fin = res['financiero']
                log = res['logistica']
                asp_c = item['Aspirantes']
                salones_c = log['Salones']
                staff_c = log['Staff Total']
                equipos_c = item.get('Equipos', 0)
                
                # Cantidades calculadas
                q_dactilo_c = math.ceil(salones_c / 4)
                q_aseo_c = math.ceil(salones_c / 6)
                
                for nombre_item, data in items_consolidado.items():
                    # Acumular Costo
                    ckey = data['cost_key']
                    if isinstance(ckey, list):
                        # Suma de múltiples claves (para FastTest)
                        costo_item = sum(fin.get(k, 0) for k in ckey)
                    else:
                        costo_item = fin.get(ckey, 0)
                    data['cost'] += costo_item
                    
                    # Acumular Cantidad
                    qtype = data['qty_type']
                    if qtype == "aspirantes":
                        data['val'] += asp_c
                    elif qtype == "aspirantes_x_formas":
                        data['val'] += asp_c * n_formas_cons
                    elif qtype == "salones":
                        data['val'] += salones_c
                    elif qtype == "staff":
                        data['val'] += staff_c
                    elif qtype == "calc_dactilo":
                        data['val'] += q_dactilo_c
                    elif qtype == "calc_aseo":
                        data['val'] += q_aseo_c
                    elif qtype == "equipos":
                        data['val'] += equipos_c
            
            # Notas explicativas según modalidad
            if es_virtual_cons:
                st.caption("💻 **Modalidad Virtual:** Los materiales de examen se han consolidado en 'Uso de plataforma FastTest' y se muestra 'Equipo de computo' en lugar de Transporte.")
            elif n_formas_cons > 1:
                st.caption(f"📝 **Nota:** Se están aplicando **{n_formas_cons} formas de prueba**, lo cual afecta las cantidades de material de examen aplicación.")
                        
            # Construir DataFrame
            rows_cons = []
            for nombre_item, data in items_consolidado.items():
                rows_cons.append({
                    "Concepto": nombre_item,
                    "Cantidad Total": data['val'],
                    "Costo Total": data['cost']
                })
                
            df_consolidado = pd.DataFrame(rows_cons)
            
            # Visualización
            st.dataframe(
                df_consolidado.style.format({
                    "Costo Total": "${:,.0f}",
                    "Cantidad Total": "{:,.0f}"
                }),
                use_container_width=True,
                hide_index=True
            )
            
            # Totalizador simple al pie
            total_cons = df_consolidado['Costo Total'].sum()
            st.caption(f"**Suma de items listados:** ${total_cons:,.0f}")


        with tab_nomina:
            st.markdown("### 👥 Nómina Detallada Global")
            st.info("📋 **Vista actual:** Detalle del personal logístico requerido para todas las ciudades.")
            # Agrupar nómina global
            nomina_global = {}
            for item in resultados_lista:
                # Reconstruir detalle de nómina desde los resultados si es necesario, 
                # pero como no guardamos el detalle crudo en resultados_lista, 
                # lo mejor es recalcular o acumular en el loop principal.
                # ESTRATEGIA: Acumular en el loop principal hubiera sido mejor, 
                # pero para no romper el flujo, recalculamos rápido o extraemos.
                # Dado que 'Staff' es un entero, necesitamos el desglose.
                
                # ESTRATEGIA: Usar el resultado pre-calculado
                
                # RE-CALCULO: OPTIMIZADO
                res_temp = item['full_res']
                for cargo in res_temp['detalle_nomina']:
                    nombre_cargo = cargo['Cargo']
                    if nombre_cargo not in nomina_global:
                        nomina_global[nombre_cargo] = {'Cantidad': 0, 'Subtotal': 0, 'Tarifa': cargo['Tarifa']}
                    
                    nomina_global[nombre_cargo]['Cantidad'] += cargo['Cantidad']
                    nomina_global[nombre_cargo]['Subtotal'] += cargo['Subtotal']
            
            # Convertir a DF
            df_nomina_global = pd.DataFrame([
                {'Cargo': k, 'Cantidad': v['Cantidad'], 'Tarifa': v['Tarifa'], 'Subtotal': v['Subtotal']}
                for k, v in nomina_global.items()
            ])
            
            st.dataframe(
                df_nomina_global.style.format({'Tarifa': '${:,.0f}', 'Subtotal': '${:,.0f}'}),
                use_container_width=True, hide_index=True
            )

        with tab_analisis:
            st.markdown("### 📊 Análisis de Costos Global")
            st.info("📋 **Vista actual:** Distribución y visualización gráfica del presupuesto nacional.")
            # Agrupar costos globales
            costos_globales = {} # Rubro -> Costo
            
            # Definir claves principales nuevas
            KEY_TRANS = 'Transporte y Distribución'
            KEY_NOMINA = 'Personal Logístico'
            KEY_TECH = 'Tecnología (Alquiler PC)'
            
            for item in resultados_lista:
                res_temp = item['full_res']
                fin = res_temp['financiero']
                
                # Agregación atómica (guardamos cada rubro individualmente)
                for k, v in fin.items():
                    if k == 'TOTAL_BASE':
                        continue
                    
                    # Estandarizar Nombres Principales para Agrupación
                    if k == KEY_TRANS:
                        key_target = 'Transporte'
                    elif k == KEY_NOMINA:
                        key_target = 'Nómina'
                    elif k == KEY_TECH:
                        key_target = 'Tecnología'
                    elif k == 'Disposición Final':
                        key_target = 'Disposición Final'
                    else:
                        # Mantener nombre original (ej: Kits, Papelería, etc.)
                        key_target = k
                    
                    costos_globales[key_target] = costos_globales.get(key_target, 0) + v

            # --- VISUALIZACIÓN GLOBAL ---
            total_costos = sum(costos_globales.values())
            
            # 1. Agrupar para Pie Chart (Resumido)
            # Aquí sumamos explícitamente los kits de aseo en una sola rebanada
            sum_aseo = costos_globales.get('Kit de Aseo', 0) + costos_globales.get('Kit para Baños', 0)
            
            # Materiales Generales (Excluyendo los 4 grandes + los 2 de aseo que ya sumamos)
            keys_excluded_pie = ['Transporte', 'Nómina', 'Tecnología', 'Disposición Final', 'Kit de Aseo', 'Kit para Baños']
            sum_materiales = sum(v for k,v in costos_globales.items() if k not in keys_excluded_pie)
            
            df_main_g = pd.DataFrame([
                {'Rubro': 'Transporte', 'Costo': costos_globales.get('Transporte', 0)},
                {'Rubro': 'Nómina', 'Costo': costos_globales.get('Nómina', 0)},
                {'Rubro': 'Aseo', 'Costo': sum_aseo},
                {'Rubro': 'Tecnología', 'Costo': costos_globales.get('Tecnología', 0)},
                {'Rubro': 'Disposición Final', 'Costo': costos_globales.get('Disposición Final', 0)},
                {'Rubro': 'Materiales', 'Costo': sum_materiales}
            ])
            
            # 2. Detalle Barras (Detallado)
            # Aquí SI queremos ver los kits de aseo sueltos, por lo que solo excluimos los 4 rubros macro
            keys_excluded_bar = ['Transporte', 'Nómina', 'Tecnología', 'Disposición Final']
            
            df_details_g = pd.DataFrame([
                {'Item': k, 'Costo': v} for k, v in costos_globales.items() if k not in keys_excluded_bar
            ]).sort_values('Costo', ascending=True)
            
            # Subplots Global
            fig_g = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'xy'}]],
                                 subplot_titles=("Presupuesto Nacional Macro", "Detalle Materiales Global"))
            
            fig_g.add_trace(go.Pie(labels=df_main_g['Rubro'], values=df_main_g['Costo'], hole=0.4,
                                 marker_colors=['#003366', '#0066CC', '#FFB347', '#FF8C00', '#6c757d', '#28a745']), row=1, col=1)
            
            fig_g.add_trace(go.Bar(x=df_details_g['Costo'], y=df_details_g['Item'], orientation='h',
                                 marker_color='#FF8C00'), row=1, col=2)
            
            fig_g.update_layout(showlegend=False, paper_bgcolor=ESAP_PALETTE['neutral_light'])

            # Layout Vertical Global
            st.dataframe(df_main_g.style.format({'Costo': '${:,.0f}'}), hide_index=True, use_container_width=True)
            st.info(f"💰 Total Global: ${total_costos:,.0f}")
            
            st.plotly_chart(fig_g, use_container_width=True)

            # Alerta Global
            if costos_globales.get('Transporte', 0) > total_global * 0.3:
                st.warning(f"⚠️ **Atención:** A nivel nacional, el transporte representa el {costos_globales.get('Transporte', 0)/total_global:.1%} del presupuesto. Considere optimizar las ciudades con logística compleja.")

        st.divider()

        # --- ANÁLISIS DE COSTOS POR CIUDAD (NUEVA SECCIÓN) ---
        st.subheader("🏙️ Análisis de Costos por Ciudad")
        
        # --- CONTROLES DE FILTRADO Y ORDEN ---
        col_filtros_1, col_filtros_2 = st.columns([3, 1])
        with col_filtros_1:
            filtro_ciudades_ui = st.multiselect(
                "🔍 Filtrar Ciudades Específicas:",
                options=[r['Ciudad'] for r in resultados_lista],
                help="Seleccione una o varias ciudades para ver su detalle."
            )
        
        with col_filtros_2:
            criterio_orden = st.selectbox(
                "🔃 Ordenar Por:",
                ["Nombre (A-Z)", "Mayor Costo Total", "Mayor Costo Unitario", "Mayor N° Aspirantes"]
            )
        
        # Lógica de Filtrado y Orden
        lista_final_ciudades = resultados_lista.copy()
        
        # 1. Filtro
        if filtro_ciudades_ui:
            lista_final_ciudades = [r for r in lista_final_ciudades if r['Ciudad'] in filtro_ciudades_ui]
        
        # 2. Orden
        if criterio_orden == "Mayor Costo Total":
            lista_final_ciudades.sort(key=lambda x: x['Costo Total'], reverse=True)
        elif criterio_orden == "Mayor Costo Unitario":
            lista_final_ciudades.sort(key=lambda x: x['Costo Unitario'], reverse=True)
        elif criterio_orden == "Mayor N° Aspirantes":
            lista_final_ciudades.sort(key=lambda x: x['Aspirantes'], reverse=True)
        else: # Nombre A-Z
            lista_final_ciudades.sort(key=lambda x: x['Ciudad'])

        st.caption(f"Mostrando **{len(lista_final_ciudades)}** ciudades.")

        for item in lista_final_ciudades:
            nombre_ciudad = item['Ciudad']
            aspirantes_ciudad = item['Aspirantes']
            modalidad_ciudad = item['Modalidad']
            costo_total_ciudad = item['Costo Total']
            
            with st.expander(f"{nombre_ciudad} ({aspirantes_ciudad} asp) - ${costo_total_ciudad:,.0f} ({modalidad_ciudad})"):
                # Recalcular detalles para esta ciudad: OPTIMIZADO
                res_ciudad = item['full_res']

                # --- KPIS LOGÍSTICOS PROPIOS DE LA CIUDAD ---
                st.markdown("#### 📦 Recursos Logísticos Locales")
                with st.container(border=True):
                    kc1, kc2, kc3, kc4 = st.columns(4)
                    kc1.metric("🏢 Sitios", res_ciudad['logistica']['Sitios'])
                    kc2.metric("🚪 Salones", res_ciudad['logistica']['Salones'])
                    
                    total_personas_c = sum([x['Cantidad'] for x in res_ciudad['detalle_nomina']])
                    kc3.metric("👥 Staff Local", total_personas_c)
                    
                    costo_impresion_viz_c = res_ciudad['financiero'].get('Material Examen Aplicación', 0) / aspirantes_ciudad
                    kc4.metric("🖨️ Tarifa Impresión", f"${costo_impresion_viz_c:,.0f}/u")
                
                st.divider()
                
                # Preparar Tabla Detallada Solicitada con Cantidades
                fin_c = res_ciudad['financiero']
                log_c = res_ciudad['logistica']
                
                # Obtener valores base para calcular cantidades
                salones_ciudad = log_c['Salones']
                sitios_ciudad = log_c['Sitios']
                staff_ciudad = log_c['Staff Total']
                q_dactilo = math.ceil(salones_ciudad / 4)
                q_aseo = math.ceil(salones_ciudad / 6)
                
                # Obtener formas de prueba y modalidad desde session_state
                n_formas = st.session_state.get('mc_formas', 1)
                es_virtual_ciudad = st.session_state.get('mc_es_virtual', False)
                equipos_ciudad = item.get('Equipos', 0)
                
                # Cantidades ajustadas por formas de prueba donde aplica
                # Material examen aplicación: aspirantes × formas (cada aspirante recibe todas las formas)
                qty_mat_examen_app = aspirantes_ciudad * n_formas
                
                # Definición de items con cantidades (Rubro, Cantidad, Costo)
                # Items base comunes a ambas modalidades
                items_detalle = [
                    ("Empaque", aspirantes_ciudad, fin_c.get('Empaque', 0)),
                    ("Kit Dactiloscopista", q_dactilo, fin_c.get('Kit Dactiloscopista', 0)),
                    ("Kit de aplicación", salones_ciudad, fin_c.get('Kit de Aplicación', 0)),
                    ("Kit de aseo", q_aseo, fin_c.get('Kit de Aseo', 0)),
                    ("Kit para baños", q_aseo, fin_c.get('Kit para Baños', 0)),
                    ("Lectura", aspirantes_ciudad, fin_c.get('Lectura y Procesamiento', 0)),
                    ("Material aplicación", salones_ciudad, fin_c.get('Material Aplicación (Papelería)', 0)),
                    ("Personal logístico", staff_ciudad, fin_c.get('Personal Logístico', 0)),
                ]
                
                # Items específicos según modalidad
                if es_virtual_ciudad:
                    # Modalidad Virtual: Fusionar materiales examen en "Uso de plataforma FastTest"
                    costo_fasttest = fin_c.get('Material Examen Aplicación', 0) + fin_c.get('Material Examen Exhibición', 0)
                    items_detalle.append(("Uso de plataforma FastTest", aspirantes_ciudad, costo_fasttest))
                    # Cambiar Transporte por Equipo de computo
                    items_detalle.append(("Equipo de computo", equipos_ciudad, fin_c.get('Tecnología (Alquiler PC)', 0)))
                else:
                    # Modalidad Impresa: Items separados
                    items_detalle.append(("Material examen aplicación", qty_mat_examen_app, fin_c.get('Material Examen Aplicación', 0)))
                    items_detalle.append(("Material examen exhibición", aspirantes_ciudad, fin_c.get('Material Examen Exhibición', 0)))
                    items_detalle.append(("Transporte", aspirantes_ciudad, fin_c.get('Transporte y Distribución', 0)))
                
                # Notas explicativas según modalidad
                if es_virtual_ciudad:
                    st.caption("💻 **Modalidad Virtual:** Los materiales de examen se muestran como 'Uso de plataforma FastTest' y se incluye 'Equipo de computo'.")
                elif n_formas > 1:
                    st.caption(f"📝 **Nota:** Se están aplicando **{n_formas} formas de prueba**, lo cual afecta las cantidades de material de examen.")

                df_display_c = pd.DataFrame(items_detalle, columns=['Rubro', 'Cantidad', 'Costo'])
                
                # Calcular costo unitario cuando la cantidad > 0
                df_display_c['Costo Unitario'] = df_display_c.apply(
                    lambda row: row['Costo'] / row['Cantidad'] if row['Cantidad'] > 0 else 0, axis=1
                )
                
                # Formatear para visualización
                df_display_c['Cantidad'] = df_display_c['Cantidad'].apply(lambda x: f"{x:,.0f}")
                df_display_c['Costo Unitario'] = df_display_c['Costo Unitario'].apply(lambda x: f"${x:,.0f}")
                df_display_c['Costo'] = df_display_c['Costo'].apply(lambda x: f"${x:,.0f}")
                
                # Layout Ciudad: Tabla y Gráfico
                c_tbl, c_graph = st.columns([1, 1])
                
                with c_tbl:
                    st.dataframe(
                        df_display_c,
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "Rubro": st.column_config.TextColumn("Concepto", width="medium"),
                            "Cantidad": st.column_config.TextColumn("Cant.", width="small"),
                            "Costo Unitario": st.column_config.TextColumn("$/Unid.", width="small"),
                            "Costo": st.column_config.TextColumn("Costo Total", width="small")
                        }
                    )
                
                with c_graph:
                    # Gráfico simple de los top 5 costos para no saturar
                    df_chart = pd.DataFrame(items_detalle, columns=['Rubro', 'Cantidad', 'Costo']).sort_values('Costo', ascending=True).tail(5)
                    fig_c = px.bar(df_chart, x='Costo', y='Rubro', orientation='h', title="Top 5 Costos Locales", text_auto='.2s')
                    fig_c.update_traces(marker_color=ESAP_PALETTE['primary'], textfont_size=10)
                    fig_c.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30, b=0), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_c, use_container_width=True, key=f"chart_ciudad_{nombre_ciudad}")

                st.info(f"💰 Total Ciudad: ${costo_total_ciudad:,.0f}")

# Footer mejorado
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="text-align: center; padding: 1rem; background: rgba(255,255,255,0.05); border-radius: 8px;">
        <p style="color: #ffffff; margin: 0; font-size: 0.8rem;">Creado con ❤️ por el equipo de</p>
        <p style="color: #FFA500; margin: 0.3rem 0 0 0; font-weight: 600;">Analítica ESAP</p>
        <p style="color: #ffffff; margin: 0.5rem 0 0 0; font-size: 0.7rem; opacity: 0.7;">© 2025 - Todos los derechos reservados</p>
    </div>
    """,
    unsafe_allow_html=True
)