"""Contrato explícito para archivos aportados por el usuario."""

import csv
from io import BytesIO, TextIOWrapper

import numpy as np
import pandas as pd

REQUIRED = ("observed_date", "fuel_type", "price")
OPTIONAL = ("department", "province", "district")


def read_csv_bytes(payload: bytes) -> pd.DataFrame:
    """Lee CSV UTF-8 sin permitir encabezados duplicados ocultados por Pandas."""
    with TextIOWrapper(BytesIO(payload), encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream), None)
    if not header:
        raise ValueError("El CSV no contiene encabezado.")
    if len(set(header)) != len(header):
        raise ValueError("El CSV contiene nombres de columnas duplicados.")
    return pd.read_csv(BytesIO(payload), encoding="utf-8-sig", low_memory=False)


def normalize(
    frame: pd.DataFrame, mapping: dict[str, str], units: dict[str, str]
) -> tuple[pd.DataFrame, dict]:
    """Valida y normaliza columnas seleccionadas; nunca infiere unidades."""
    missing = [key for key in REQUIRED if key not in mapping or mapping[key] not in frame]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Cada campo debe corresponder a una columna diferente.")
    if frame.columns.duplicated().any():
        raise ValueError("El CSV contiene nombres de columnas duplicados.")
    if len(frame) > 1_000_000:
        raise ValueError("El CSV supera el límite de un millón de filas de esta versión.")
    selected = {source: target for target, source in mapping.items() if source in frame}
    data = frame.rename(columns=selected)[list(selected.values())].copy()
    data["observed_date"] = pd.to_datetime(
        data["observed_date"], errors="coerce", dayfirst=True, format="mixed"
    )
    data["price"] = pd.to_numeric(data["price"], errors="coerce")
    data["price"] = data["price"].where(np.isfinite(data["price"]))
    data["fuel_type"] = data["fuel_type"].astype("string").str.strip()
    data["price_unit"] = data["fuel_type"].map(units)
    valid = (
        data["observed_date"].notna()
        & data["price"].notna()
        & data["price"].gt(0)
        & data["fuel_type"].notna()
        & data["fuel_type"].ne("")
        & data["price_unit"].notna()
        & data["price_unit"].ne("")
    ).fillna(False)
    report = {
        "raw_rows": len(frame),
        "valid_rows": int(valid.sum()),
        "excluded_rows": int((~valid).sum()),
        "missing_dates": int(data["observed_date"].isna().sum()),
        "missing_or_invalid_prices": int(data["price"].isna().sum()),
        "zero_or_negative_prices": int(data["price"].le(0).sum()),
        "missing_units": int(data["price_unit"].isna().sum()),
    }
    return data.loc[valid].reset_index(drop=True), report


def normalize_wide(
    frame: pd.DataFrame,
    mapping: dict[str, str],
    price_columns: list[str],
    units: dict[str, str],
) -> tuple[pd.DataFrame, dict]:
    """Convierte columnas de precios explícitas en observaciones por combustible."""
    if "observed_date" not in mapping or mapping["observed_date"] not in frame:
        raise ValueError("Falta la columna obligatoria de fecha observada.")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Cada campo base debe corresponder a una columna diferente.")
    if frame.columns.duplicated().any():
        raise ValueError("El CSV contiene nombres de columnas duplicados.")
    if not price_columns:
        raise ValueError("Selecciona al menos una columna de precio.")
    if len(set(price_columns)) != len(price_columns):
        raise ValueError("Las columnas de precio no deben repetirse.")
    used = set(mapping.values())
    if any(column not in frame or column in used for column in price_columns):
        raise ValueError("Las columnas de precio deben existir y ser distintas de los campos base.")
    base = frame[list(mapping.values()) + price_columns].rename(
        columns={source: target for target, source in mapping.items()}
    )
    long = base.melt(
        id_vars=list(mapping),
        value_vars=price_columns,
        var_name="fuel_type",
        value_name="price",
    )
    identity = {key: key for key in (*mapping, "fuel_type", "price")}
    data, report = normalize(long, identity, units)
    report["source_rows"] = len(frame)
    return data, report


def filter_data(
    data: pd.DataFrame, fuel: str, start, end, department: str | None = None
) -> pd.DataFrame:
    if start > end:
        raise ValueError("La fecha inicial debe ser anterior o igual a la final.")
    mask = data["fuel_type"].eq(fuel) & data["observed_date"].dt.date.between(start, end)
    if department and "department" in data:
        mask &= data["department"].eq(department)
    return data.loc[mask].copy()


def summary(data: pd.DataFrame) -> dict:
    if data.empty:
        raise ValueError("No hay observaciones válidas para resumir.")
    if data[["fuel_type", "price_unit"]].drop_duplicates().shape[0] != 1:
        raise ValueError("La mediana requiere un solo combustible y unidad.")
    prices = data["price"]
    return {
        "count": len(data),
        "median": float(prices.median()),
        "p25": float(prices.quantile(0.25)),
        "p75": float(prices.quantile(0.75)),
        "last_observed": data["observed_date"].max().date(),
    }
