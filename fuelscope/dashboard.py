"""Interfaz de exploración local con atribución explícita."""

import json
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from fuelscope.data import (
    OPTIONAL,
    REQUIRED,
    filter_data,
    normalize,
    normalize_wide,
    read_csv_bytes,
    summary,
)
from fuelscope.snapshot import read_snapshot

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
SOURCE_URL = (
    "https://www.datosabiertos.gob.pe/dataset/"
    "lista-de-precios-de-combustibles-diaria-reconstruida-"
    "partir-de-los-precios-actualizados"
)
FUEL_LABELS = {
    "g_regular": "Gasolina o gasohol regular",
    "g_premium": "Gasolina o gasohol premium",
    "diesel": "Diésel DB5-S",
    "gnv": "Gas natural vehicular",
    "glp_g": "GLP a granel",
    "glp_e": "GLP envasado (balón de 10 kg)",
}

INK = "#173a42"
TEAL = "#087e80"


def spanish_number(value: float | int, decimals: int = 0) -> str:
    """Muestra cifras con separadores habituales en español."""
    return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def metric_card(label: str, value: str, detail: str) -> None:
    st.markdown(
        '<div class="fs-metric">'
        f'<div class="fs-metric-label">{escape(label)}</div>'
        f'<div class="fs-metric-value">{escape(value)}</div>'
        f'<div class="fs-metric-detail">{escape(detail)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def page_style() -> None:
    st.markdown(
        """<style>
        .block-container{max-width:1260px;padding-top:1.3rem;padding-bottom:3rem}
        [data-testid="stSidebar"]{background:#f2f7f6;border-right:1px solid #e0eae8}
        [data-testid="stSidebar"] .block-container{padding-top:1.8rem}
        .fs-hero{padding:1.8rem 2rem;border-radius:20px;
          background:linear-gradient(120deg,#103a43 0%,#0d6066 72%,#138683 100%);
          color:#fff;box-shadow:0 10px 30px rgba(16,58,67,.12);margin-bottom:1.1rem}
        .fs-eyebrow{font-size:.73rem;letter-spacing:.13em;font-weight:750;
          text-transform:uppercase;color:#b8e7df;margin-bottom:.5rem}
        .fs-hero h1{font-size:clamp(2.2rem,4vw,3.1rem);line-height:1.05;
          color:#fff;margin:0 0 .45rem;font-weight:760}
        .fs-hero p{color:#e0f1ef;font-size:1.02rem;margin:0;max-width:770px}
        .fs-hero-meta{display:flex;flex-wrap:wrap;gap:.55rem;margin-top:1.25rem}
        .fs-pill{display:inline-block;padding:.34rem .7rem;border:1px solid #84bdbb;
          border-radius:999px;color:#f4ffff;font-size:.79rem;font-weight:650}
        .fs-section{margin:1.7rem 0 .25rem;color:#173a42;font-size:1.36rem;font-weight:740}
        .fs-section-sub{color:#617c82;font-size:.91rem;margin-bottom:1rem}
        .fs-metric{background:#fff;border:1px solid #dce9e7;border-top:3px solid #0d8988;
          border-radius:14px;padding:1rem 1.1rem;min-height:145px;
          box-shadow:0 5px 18px rgba(20,62,69,.045);margin-bottom:.35rem}
        .fs-metric-label{font-size:.81rem;color:#607b81;font-weight:650;min-height:2.25rem}
        .fs-metric-value{font-size:clamp(1.5rem,2.6vw,2.15rem);font-weight:760;
          color:#173a42;line-height:1.12;white-space:nowrap}
        .fs-metric-detail{font-size:.73rem;color:#6c858a;margin-top:.55rem;
          line-height:1.3;overflow-wrap:anywhere}
        .fs-note{color:#667f85;font-size:.82rem;line-height:1.45;margin:.45rem 0 1rem}
        @media(max-width:800px){.fs-hero{padding:1.35rem 1.25rem}.fs-metric{min-height:125px}}
        </style>""",
        unsafe_allow_html=True,
    )


def hero(end_date: str, *, uploaded: bool = False) -> None:
    tag = "CSV de esta sesión" if uploaded else "Datos oficiales históricos"
    date_chip = f"Último dato: {end_date}" if not uploaded else f"Cobertura hasta {end_date}"
    st.markdown(
        '<div class="fs-hero">'
        '<div class="fs-eyebrow">Observatorio de combustibles · Perú</div>'
        "<h1>FuelScope</h1>"
        "<p>Explora precios reportados, tendencias y cobertura con el contexto de cada dato.</p>"
        f'<div class="fs-hero-meta"><span class="fs-pill">{escape(tag)}</span>'
        f'<span class="fs-pill">{escape(date_chip)}</span></div></div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    page_style()
    try:
        snapshot = read_snapshot(Path("data/processed"))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        st.error(f"El snapshot local no pasó la verificación de integridad: {exc}")
        return
    if snapshot is not None:
        data, manifest = snapshot
        with st.sidebar:
            st.markdown("### FuelScope")
            mode = st.radio(
                "Fuente de datos",
                ["Datos incluidos", "Subir CSV"],
            )
        if mode == "Datos incluidos":
            hero(manifest["observation_max_date"])
            render_analysis(
                data,
                manifest["quality"],
                source_file="snapshot local",
                source_url=manifest["dataset_url"],
                source_license=manifest["license"],
                manifest=manifest,
            )
            return
    upload = st.file_uploader("Cargar CSV de precios históricos", type="csv")
    if upload is None:
        hero("sin datos", uploaded=True)
        st.info(
            "Sube un CSV para explorar datos propios. "
            "El snapshot oficial sigue disponible en la barra lateral."
        )
        return
    if upload.size > MAX_UPLOAD_BYTES:
        st.error("El archivo supera el límite de 50 MB de esta versión.")
        return
    try:
        frame = read_csv_bytes(upload.getvalue())
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        st.error(f"No se pudo leer el CSV en UTF-8: {exc}")
        return
    if frame.empty:
        st.warning("El archivo no contiene registros.")
        return
    if frame.columns.duplicated().any() or len(frame) > 1_000_000:
        st.error("El CSV tiene columnas duplicadas o supera un millón de filas.")
        return
    st.caption(
        f"Archivo cargado en esta sesión: {upload.name} · {len(frame):,} filas. "
        "La procedencia no se verifica automáticamente."
    )
    source_url = st.text_input("URL de origen del archivo (declarada por quien lo carga)")
    source_license = st.text_input("Licencia del archivo (declarada por quien lo carga)")
    st.markdown("### Contrato de datos")
    st.write(
        "Selecciona las columnas reales según el diccionario del archivo. "
        "Los precios iguales a cero se excluyen hasta confirmar su significado."
    )
    layout = st.radio(
        "Organización del CSV",
        ["Una fila por precio", "Una columna de precio por combustible"],
        horizontal=True,
    )
    columns = [""] + list(frame.columns)
    mapping = {}
    cols = st.columns(3)
    labels = {
        "observed_date": "Fecha observada",
        "fuel_type": "Tipo de combustible",
        "price": "Precio",
        "department": "Departamento",
        "province": "Provincia",
        "district": "Distrito",
    }
    fields = (
        (*REQUIRED, *OPTIONAL) if layout == "Una fila por precio" else ("observed_date", *OPTIONAL)
    )
    for index, key in enumerate(fields):
        chosen = cols[index % 3].selectbox(labels[key], columns, key=f"map_{key}")
        if chosen:
            mapping[key] = chosen
    if layout == "Una fila por precio":
        if any(key not in mapping for key in REQUIRED):
            st.info("Asigna fecha, combustible y precio para continuar.")
            return
        fuels = sorted(frame[mapping["fuel_type"]].dropna().astype(str).str.strip().unique())
        price_columns = []
    else:
        if "observed_date" not in mapping:
            st.info("Asigna la fecha observada para continuar.")
            return
        price_columns = st.multiselect(
            "Columnas que representan precios de combustibles",
            [column for column in frame if column not in mapping.values()],
        )
        fuels = price_columns
        if not price_columns:
            st.info("Selecciona al menos una columna de precio.")
            return
    if len(fuels) > 50:
        st.error("La columna de combustible tiene demasiadas categorías; revisa el mapeo.")
        return
    st.markdown("**Unidad documentada por combustible**")
    units = {
        fuel: st.text_input(f"{fuel} — unidad (por ejemplo, S/ por galón)", key=f"unit_{fuel}")
        for fuel in fuels
    }
    if not all(units.values()):
        st.info("Confirma todas las unidades según el diccionario para habilitar el análisis.")
        return
    try:
        if layout == "Una fila por precio":
            data, report = normalize(frame, mapping, units)
        else:
            data, report = normalize_wide(frame, mapping, price_columns, units)
    except ValueError as exc:
        st.error(str(exc))
        return
    if data.empty:
        st.warning("No hay observaciones válidas después de aplicar el contrato.")
        return
    hero(str(data["observed_date"].max().date()), uploaded=True)
    render_analysis(
        data,
        report,
        source_file=upload.name,
        source_url=source_url,
        source_license=source_license,
    )


def render_analysis(
    data: pd.DataFrame,
    report: dict,
    source_file: str,
    source_url: str,
    source_license: str,
    manifest: dict | None = None,
) -> None:
    first_date = data["observed_date"].min().date()
    last_date = data["observed_date"].max().date()
    with st.sidebar:
        st.markdown("### Filtros")
        fuel = st.selectbox(
            "Combustible",
            sorted(
                data["fuel_type"].unique(),
                key=lambda value: (
                    value not in FUEL_LABELS,
                    list(FUEL_LABELS).index(value) if value in FUEL_LABELS else value,
                ),
            ),
            format_func=lambda value: FUEL_LABELS.get(value, value),
        )
        dates = st.date_input(
            "Período observado",
            value=(first_date, last_date),
            min_value=first_date,
            max_value=last_date,
            help="El selector termina en la última fecha presente en el archivo.",
        )
        st.caption(f"Cobertura del archivo: {first_date:%d/%m/%Y}–{last_date:%d/%m/%Y}")
        department = None
        if "department" in data:
            places = ["Todos"] + sorted(data["department"].dropna().astype(str).unique())
            selected = st.selectbox("Departamento", places)
            department = None if selected == "Todos" else selected
    if len(dates) != 2:
        st.info("Selecciona fecha inicial y final.")
        return
    try:
        filtered = filter_data(data, fuel, dates[0], dates[1], department)
    except ValueError as exc:
        st.warning(str(exc))
        return
    if filtered.empty:
        st.warning("No hay registros para los filtros seleccionados.")
        return
    unit = str(filtered["price_unit"].iloc[0])
    stats = summary(filtered)
    st.markdown('<div class="fs-section">Panorama</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="fs-section-sub">{escape(FUEL_LABELS.get(fuel, fuel))} · '
        f"{dates[0]:%d/%m/%Y}–{dates[1]:%d/%m/%Y} · "
        f"último registro {stats['last_observed']:%d/%m/%Y}</div>",
        unsafe_allow_html=True,
    )
    metrics = st.columns(4)
    with metrics[0]:
        metric_card("Precio mediano", spanish_number(stats["median"], 2), unit)
    with metrics[1]:
        metric_card(
            "Observaciones", spanish_number(stats["count"]), "Precios reportados en el filtro"
        )
    with metrics[2]:
        metric_card(
            "Rango intercuartílico",
            spanish_number(stats["p75"] - stats["p25"], 2),
            f"P25–P75 · {unit}",
        )
    with metrics[3]:
        metric_card(
            "Días con datos",
            spanish_number(filtered["observed_date"].dt.date.nunique()),
            "Fechas con al menos un reporte",
        )
    if manifest:
        st.markdown(
            '<div class="fs-note">Precios reportados, no ventas. La unidad física no está '
            "documentada en el diccionario oficial de este archivo.</div>",
            unsafe_allow_html=True,
        )
    daily = (
        filtered.assign(day=filtered["observed_date"].dt.date)
        .groupby("day", as_index=False)
        .agg(price=("price", "median"), observations=("price", "size"))
    )
    st.markdown('<div class="fs-section">Evolución diaria</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="fs-section-sub">Mediana y cantidad de precios '
        "reportados por fecha observada.</div>",
        unsafe_allow_html=True,
    )
    daily["hover_date"] = pd.to_datetime(daily["day"]).dt.strftime("%d/%m/%Y")
    daily["hover_price"] = daily["price"].map(lambda value: spanish_number(value, 2))
    fig = go.Figure(
        go.Scatter(
            x=daily["day"],
            y=daily["price"],
            mode="lines+markers",
            line={"color": TEAL, "width": 3},
            marker={"color": TEAL, "size": 5},
            customdata=daily[["hover_date", "hover_price"]].to_numpy(),
            hovertemplate="%{customdata[0]}<br>Mediana: %{customdata[1]}<extra></extra>",
        )
    )
    fig.update_layout(
        height=360,
        margin={"l": 8, "r": 8, "t": 10, "b": 15},
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Arial, sans-serif", "color": INK},
        hovermode="x unified",
        xaxis={"title": None, "showgrid": False, "tickformat": "%d %b", "linecolor": "#c9d9d8"},
        yaxis={"title": "Precio reportado", "gridcolor": "#e9f0ef", "zeroline": False},
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(f"Unidad de precio: {unit}. Cada punto es la mediana de los reportes de ese día.")
    coverage, interpretation = st.columns([3, 2], gap="large")
    with coverage:
        st.markdown("#### Cobertura de reportes")
        volume = px.bar(daily, x="day", y="observations")
        volume.update_traces(
            marker_color="#66a9a5", hovertemplate="%{x|%d/%m/%Y}<br>%{y:,} reportes<extra></extra>"
        )
        volume.update_layout(
            height=250,
            margin={"l": 5, "r": 5, "t": 10, "b": 10},
            paper_bgcolor="white",
            plot_bgcolor="white",
            font={"family": "Arial, sans-serif", "color": INK},
            xaxis={"title": None, "showgrid": False, "tickformat": "%d %b"},
            yaxis={"title": "Reportes", "gridcolor": "#e9f0ef", "zeroline": False},
        )
        st.plotly_chart(volume, width="stretch", config={"displayModeBar": False})
    with interpretation:
        st.markdown("#### Cómo leer estas cifras")
        st.write(
            "La mediana resume precios publicados para un combustible; "
            "no es un promedio ponderado por ventas. El rango intercuartílico "
            "muestra la distancia entre los percentiles 25 y 75."
        )
        st.write("Compara fechas dentro de un mismo combustible y unidad.")
    if "department" in filtered:
        ranking = filtered.groupby("department", as_index=False).agg(
            median=("price", "median"), observations=("price", "size")
        )
        minimum = st.number_input("Mínimo de observaciones por departamento", min_value=1, value=10)
        ranking = ranking.loc[ranking["observations"] >= minimum].sort_values("median")
        if ranking.empty:
            st.info("Ningún departamento alcanza el mínimo de muestra seleccionado.")
        else:
            chart = px.bar(
                ranking,
                x="median",
                y="department",
                orientation="h",
                hover_data=["observations"],
                title="Mediana por departamento",
            )
            chart.update_layout(xaxis_title=f"Precio ({unit})", yaxis_title="Departamento")
            st.plotly_chart(chart, width="stretch", config={"displayModeBar": False})
    st.markdown("### Explorar datos")
    with st.expander("Ver registros y descargar datos"):
        st.dataframe(filtered.head(1000), width="stretch", hide_index=True)
        st.caption(
            "La vista previa muestra hasta 1.000 filas; "
            "la descarga incluye todos los registros filtrados."
        )
        st.download_button(
            "Descargar CSV filtrado",
            filtered.to_csv(index=False).encode("utf-8-sig"),
            file_name="fuelscope_filtrado.csv",
            mime="text/csv",
        )
    metadata = {
        "file_name": source_file,
        "declared_source_url": source_url or None,
        "declared_license": source_license or None,
        "source_verified_by_app": False,
        "fuel_type": fuel,
        "price_unit": unit,
        "start_date": dates[0].isoformat(),
        "end_date": dates[1].isoformat(),
        "department": department,
        "row_count": len(filtered),
        "quality": report,
    }
    with st.expander("Descargar metadatos de la exportación"):
        st.download_button(
            "Descargar metadatos de la exportación",
            json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="fuelscope_metadatos.json",
            mime="application/json",
        )
    with st.expander("Fuente, vigencia y calidad de datos"):
        st.markdown(
            f"**Fuente:** [Catálogo de datos abiertos de OSINERGMIN]({SOURCE_URL})"
            if manifest
            else "**Fuente:** archivo cargado por la persona usuaria; "
            "procedencia no verificada por la aplicación."
        )
        st.write(f"Cobertura observada: {first_date:%d/%m/%Y}–{last_date:%d/%m/%Y}.")
        if manifest:
            st.write(
                "El archivo publicado como `precios_combustibles_anonimizados_20260301_part1.csv` "
                "contiene observaciones solo hasta el 28/02/2026. "
                "La consulta semanal vuelve a comprobar esta URL fija; no incorpora "
                "automáticamente nuevos archivos con otros nombres."
            )
            st.write(
                f"Versión: `{manifest['version_id'][:12]}` · "
                f"ingesta: {manifest['ingested_at_utc']} · licencia: {source_license}."
            )
            st.write(
                "Este CSV no incluye departamento; el diccionario no define "
                "la unidad física. Para precios vigentes, consulta Facilito."
            )
        else:
            st.write(
                f"URL declarada: {source_url or 'no indicada'} · "
                f"licencia declarada: {source_license or 'no indicada'}."
            )
        st.json(report)
