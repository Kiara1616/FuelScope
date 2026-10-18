"""Interfaz de exploración local con atribución explícita."""

import json
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from fuelscope.data import OPTIONAL, REQUIRED, filter_data, normalize, summary
from fuelscope.snapshot import read_snapshot

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
SOURCE_URL = (
    "https://www.datosabiertos.gob.pe/dataset/"
    "lista-de-precios-de-combustibles-diaria-reconstruida-"
    "partir-de-los-precios-actualizados"
)


def render() -> None:
    st.markdown(
        "<style>"
        ".block-container{padding-top:2rem;max-width:1400px}"
        "h1{color:#123d46}"
        "div[data-testid='stMetric']{background:#eff7f6;padding:1rem;"
        "border-radius:.7rem;border-left:4px solid #117c83}"
        "</style>",
        unsafe_allow_html=True,
    )
    st.title("FuelScope")
    st.subheader("Observatorio de precios de combustibles en Perú")
    st.info(
        "Datos abiertos históricos reportados. "
        "No sustituyen la consulta de precios vigentes en el establecimiento."
    )
    st.caption(
        "La descarga automática oficial está bloqueada en este entorno. "
        "Para explorar precios, carga un CSV obtenido legítimamente y verifica "
        "sus columnas y unidades con el diccionario de la fuente."
    )
    try:
        snapshot = read_snapshot(Path("data/processed"))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        st.error(f"El snapshot local no pasó la verificación de integridad: {exc}")
        return
    if snapshot is not None:
        data, manifest = snapshot
        st.caption(
            f"Snapshot local {manifest['version_id'][:12]} · "
            f"última observación {manifest['observation_max_date']} · "
            f"ingesta {manifest['ingested_at_utc']}. "
            "La procedencia declarada requiere verificación externa."
        )
        render_analysis(
            data,
            manifest["quality"],
            source_file="snapshot local",
            source_url=manifest["dataset_url"],
            source_license=manifest["license"],
        )
        return
    upload = st.file_uploader("Cargar CSV de precios históricos", type="csv")
    if upload is None:
        st.warning(
            "Fuente no actualizada: aún no hay un conjunto oficial verificado en esta versión."
        )
        st.markdown(
            f"**Fuente prevista:** [OSINERGMIN — catálogo de precios]({SOURCE_URL}) · "
            f"[Diccionario]({SOURCE_URL}-2) · "
            "Licencia: Open Data Commons Attribution License"
        )
        return
    if upload.size > MAX_UPLOAD_BYTES:
        st.error("El archivo supera el límite de 50 MB de esta versión.")
        return
    try:
        frame = pd.read_csv(BytesIO(upload.getvalue()), encoding="utf-8", low_memory=False)
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
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
    for index, key in enumerate((*REQUIRED, *OPTIONAL)):
        chosen = cols[index % 3].selectbox(labels[key], columns, key=f"map_{key}")
        if chosen:
            mapping[key] = chosen
    if any(key not in mapping for key in REQUIRED):
        st.info("Asigna fecha, combustible y precio para continuar.")
        return
    fuels = sorted(frame[mapping["fuel_type"]].dropna().astype(str).str.strip().unique())
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
        data, report = normalize(frame, mapping, units)
    except ValueError as exc:
        st.error(str(exc))
        return
    if data.empty:
        st.warning("No hay observaciones válidas después de aplicar el contrato.")
        return
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
) -> None:
    with st.sidebar:
        st.header("Filtros")
        fuel = st.selectbox("Combustible", sorted(data["fuel_type"].unique()))
        dates = st.date_input(
            "Período observado",
            value=(data["observed_date"].min().date(), data["observed_date"].max().date()),
        )
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
    st.markdown("### Resumen")
    metrics = st.columns(4)
    metrics[0].metric(
        "Observaciones válidas",
        f"{stats['count']:,}",
        help="Registros del combustible, unidad, territorio y período seleccionados.",
    )
    metrics[1].metric(
        "Precio mediano",
        f"{stats['median']:,.2f} {unit}",
        help="Mediana de precios reportados, no de transacciones.",
    )
    metrics[2].metric(
        "Brecha intercuartílica",
        f"{stats['p75'] - stats['p25']:,.2f} {unit}",
        help="Percentil 75 menos percentil 25.",
    )
    metrics[3].metric("Última observación", str(stats["last_observed"]))
    daily = (
        filtered.assign(day=filtered["observed_date"].dt.date)
        .groupby("day", as_index=False)["price"]
        .median()
    )
    fig = px.line(daily, x="day", y="price", markers=True, title="Mediana por día observado")
    fig.update_layout(
        xaxis_title="Fecha observada", yaxis_title=f"Precio ({unit})", plot_bgcolor="white"
    )
    st.plotly_chart(fig, use_container_width=True)
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
            st.plotly_chart(chart, use_container_width=True)
    st.markdown("### Explorar datos")
    st.dataframe(filtered.head(1000), use_container_width=True, hide_index=True)
    st.caption(
        "La tabla muestra hasta 1 000 filas; la descarga incluye todos los registros "
        "filtrados. Procedencia y licencia del archivo cargado deben confirmarse "
        "con su proveedor."
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
    st.download_button(
        "Descargar metadatos de la exportación",
        json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="fuelscope_metadatos.json",
        mime="application/json",
    )
    with st.expander("Estado y calidad"):
        st.json(report)
        st.write(
            "Fuente no actualizada automáticamente. Fechas de publicación e ingesta "
            "no verificadas para el archivo cargado."
        )
