"""Contrato explícito para archivos aportados por el usuario."""
import pandas as pd

REQUIRED = ("observed_date", "fuel_type", "price")
OPTIONAL = ("department", "province", "district")


def normalize(frame: pd.DataFrame, mapping: dict[str, str], units: dict[str, str]) -> tuple[pd.DataFrame, dict]:
    """Valida y normaliza columnas seleccionadas; nunca infiere unidades."""
    missing = [key for key in REQUIRED if key not in mapping or mapping[key] not in frame]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Cada campo debe corresponder a una columna diferente.")
    selected = {source: target for target, source in mapping.items() if source in frame}
    data = frame.rename(columns=selected)[list(selected.values())].copy()
    data["observed_date"] = pd.to_datetime(data["observed_date"], errors="coerce", dayfirst=True)
    data["price"] = pd.to_numeric(data["price"], errors="coerce")
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
    report = {"raw_rows": len(frame), "valid_rows": int(valid.sum()), "excluded_rows": int((~valid).sum())}
    return data.loc[valid].reset_index(drop=True), report


def filter_data(data: pd.DataFrame, fuel: str, start, end, department: str | None = None) -> pd.DataFrame:
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
