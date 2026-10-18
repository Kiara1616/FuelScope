import json

import pandas as pd
import pytest

from fuelscope.snapshot import publish_snapshot, read_snapshot

MAPPING = {"observed_date": "fecha", "fuel_type": "tipo", "price": "valor"}
UNITS = {"GNV": "S/ por m³"}


def test_publish_is_idempotent_and_readable(tmp_path):
    csv_path = tmp_path / "source.csv"
    pd.DataFrame({"fecha": ["01/01/2026"], "tipo": ["GNV"], "valor": [2.5]}).to_csv(
        csv_path, index=False
    )
    root = tmp_path / "processed"
    status, manifest = publish_snapshot(
        csv_path, root, MAPPING, UNITS, "https://example.org", "ODC-BY"
    )
    assert status == "updated"
    first_pointer = (root / "current.json").read_bytes()
    first_manifest = (root / manifest["version_id"] / "manifest.json").read_bytes()
    status, second = publish_snapshot(
        csv_path, root, MAPPING, UNITS, "https://example.org", "ODC-BY"
    )
    assert status == "no_change"
    assert second == manifest
    assert (root / "current.json").read_bytes() == first_pointer
    assert (root / manifest["version_id"] / "manifest.json").read_bytes() == first_manifest
    data, loaded_manifest = read_snapshot(root)
    assert data["price"].tolist() == [2.5]
    assert loaded_manifest == manifest


def test_invalid_update_preserves_previous_snapshot(tmp_path):
    csv_path = tmp_path / "source.csv"
    root = tmp_path / "processed"
    pd.DataFrame({"fecha": ["01/01/2026"], "tipo": ["GNV"], "valor": [2.5]}).to_csv(
        csv_path, index=False
    )
    publish_snapshot(csv_path, root, MAPPING, UNITS, "https://example.org", "ODC-BY")
    pointer_before = (root / "current.json").read_bytes()
    pd.DataFrame({"fecha": ["fecha rota"], "tipo": ["GNV"], "valor": [2.5]}).to_csv(
        csv_path, index=False
    )
    with pytest.raises(ValueError, match="se conserva"):
        publish_snapshot(csv_path, root, MAPPING, UNITS, "https://example.org", "ODC-BY")
    assert (root / "current.json").read_bytes() == pointer_before


def test_integrity_failure_is_detected(tmp_path):
    csv_path = tmp_path / "source.csv"
    root = tmp_path / "processed"
    pd.DataFrame({"fecha": ["01/01/2026"], "tipo": ["GNV"], "valor": [2.5]}).to_csv(
        csv_path, index=False
    )
    _, manifest = publish_snapshot(csv_path, root, MAPPING, UNITS, "https://example.org", "ODC-BY")
    file_path = root / manifest["version_id"] / "data.parquet"
    file_path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integridad"):
        read_snapshot(root)


def test_changed_contract_creates_new_version(tmp_path):
    csv_path = tmp_path / "source.csv"
    root = tmp_path / "processed"
    pd.DataFrame({"fecha": ["01/01/2026"], "tipo": ["GNV"], "valor": [2.5]}).to_csv(
        csv_path, index=False
    )
    _, first = publish_snapshot(csv_path, root, MAPPING, UNITS, "https://example.org", "ODC-BY")
    _, second = publish_snapshot(csv_path, root, MAPPING, UNITS, "https://example.org/v2", "ODC-BY")
    assert first["version_id"] != second["version_id"]
    assert json.loads((root / "current.json").read_text())["version"] == second["version_id"]
