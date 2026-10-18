from datetime import date

import pandas as pd
import pytest

from fuelscope.data import filter_data, normalize, summary


def test_normalize_excludes_missing_and_zero_prices():
    raw = pd.DataFrame(
        {"fecha": ["01/01/2026"] * 4, "tipo": ["GNV"] * 4, "valor": [2.0, 4.0, None, 0]}
    )
    data, report = normalize(
        raw, {"observed_date": "fecha", "fuel_type": "tipo", "price": "valor"}, {"GNV": "S/ por m³"}
    )
    assert report["raw_rows"] == 4
    assert report["valid_rows"] == 2
    assert report["excluded_rows"] == 2
    assert report["missing_or_invalid_prices"] == 1
    assert report["zero_or_negative_prices"] == 1
    assert summary(data)["median"] == 3
    assert summary(data)["count"] == 2


def test_filter_keeps_one_fuel_and_date():
    raw = pd.DataFrame(
        {
            "fecha": ["01/01/2026", "01/01/2026", "02/01/2026"],
            "tipo": ["GNV", "GLP", "GNV"],
            "valor": [2, 9, 3],
        }
    )
    data, _ = normalize(
        raw,
        {"observed_date": "fecha", "fuel_type": "tipo", "price": "valor"},
        {"GNV": "S/ por m³", "GLP": "S/ por galón"},
    )
    result = filter_data(data, "GNV", date(2026, 1, 1), date(2026, 1, 1))
    assert result["price"].tolist() == [2]


def test_required_mapping_and_inverted_dates():
    raw = pd.DataFrame({"fecha": ["01/01/2026"]})
    with pytest.raises(ValueError, match="Faltan columnas"):
        normalize(raw, {"observed_date": "fecha"}, {})
    with pytest.raises(ValueError, match="fecha inicial"):
        filter_data(pd.DataFrame(), "GNV", date(2026, 1, 2), date(2026, 1, 1))


def test_invalid_dates_and_units_are_reported():
    raw = pd.DataFrame(
        {"fecha": ["fecha rota", "03/01/2026"], "tipo": ["GNV", "GLP"], "valor": [3, 4]}
    )
    data, report = normalize(
        raw, {"observed_date": "fecha", "fuel_type": "tipo", "price": "valor"}, {"GNV": "S/ por m³"}
    )
    assert data.empty
    assert report["missing_dates"] == 1
    assert report["missing_units"] == 1


def test_summary_rejects_mixed_fuels_and_units():
    raw = pd.DataFrame({"fecha": ["01/01/2026"] * 2, "tipo": ["GNV", "GLP"], "valor": [2, 4]})
    data, _ = normalize(
        raw,
        {"observed_date": "fecha", "fuel_type": "tipo", "price": "valor"},
        {"GNV": "S/ por m³", "GLP": "S/ por galón"},
    )
    with pytest.raises(ValueError, match="un solo combustible"):
        summary(data)


def test_duplicate_mapping_rejected():
    raw = pd.DataFrame({"a": ["01/01/2026"], "b": [3]})
    with pytest.raises(ValueError, match="columna diferente"):
        normalize(raw, {"observed_date": "a", "fuel_type": "a", "price": "b"}, {"GNV": "S/ por m³"})
