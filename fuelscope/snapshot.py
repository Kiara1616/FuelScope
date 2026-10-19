"""Publicación inmutable y lectura de snapshots aprobados manualmente."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from fuelscope.data import normalize, normalize_wide, read_csv_bytes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_snapshot(root: Path) -> tuple[pd.DataFrame, dict] | None:
    pointer = root / "current.json"
    if not pointer.exists():
        return None
    current = json.loads(pointer.read_text(encoding="utf-8"))
    version = current["version"]
    if (
        not isinstance(version, str)
        or len(version) != 64
        or any(character not in "0123456789abcdef" for character in version)
    ):
        raise ValueError("El identificador del snapshot no es válido.")
    folder = root / version
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    data_path = folder / "data.parquet"
    if manifest["version_id"] != version:
        raise ValueError("El manifiesto no coincide con el snapshot activo.")
    if manifest["parquet_sha256"] != sha256_file(data_path):
        raise ValueError("La integridad del archivo Parquet no coincide con el manifiesto.")
    return pd.read_parquet(data_path), manifest


def publish_snapshot(
    csv_path: Path,
    root: Path,
    mapping: dict[str, str],
    units: dict[str, str],
    source_url: str,
    license_name: str,
    price_columns: list[str] | None = None,
) -> tuple[str, dict]:
    """Publica un snapshot local; mismo CSV produce no_change sin escrituras."""
    if not source_url or not license_name:
        raise ValueError("Se requieren URL de origen y licencia declaradas.")
    if csv_path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("El CSV supera el límite de 50 MB de esta versión.")
    source_hash = sha256_file(csv_path)
    contract = {
        "mapping": mapping,
        "units": units,
        "source_url": source_url,
        "license": license_name,
        "price_columns": price_columns,
    }
    fingerprint = source_hash + json.dumps(contract, sort_keys=True, ensure_ascii=False)
    version = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    pointer = root / "current.json"
    if pointer.exists():
        current = json.loads(pointer.read_text(encoding="utf-8"))
        if current.get("version") == version:
            existing = json.loads((root / version / "manifest.json").read_text(encoding="utf-8"))
            if existing["parquet_sha256"] != sha256_file(root / version / "data.parquet"):
                raise ValueError("El snapshot existente no pasó la verificación de integridad.")
            return "no_change", existing
    raw = read_csv_bytes(csv_path.read_bytes())
    if price_columns is None:
        data, quality = normalize(raw, mapping, units)
    else:
        data, quality = normalize_wide(raw, mapping, price_columns, units)
    if data.empty:
        raise ValueError(
            "El CSV no contiene observaciones válidas; se conserva el snapshot anterior."
        )
    root.mkdir(parents=True, exist_ok=True)
    version_dir = root / version
    if not version_dir.exists():
        build_dir = Path(tempfile.mkdtemp(prefix="build-", dir=root))
        try:
            data_path = build_dir / "data.parquet"
            data.sort_values(list(data.columns), kind="stable").to_parquet(data_path, index=False)
            manifest = {
                "publisher": "Declarado por operador; sin verificación automática",
                "dataset_url": source_url,
                "license": license_name,
                "retrieved_at_utc": None,
                "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_published_at": None,
                "observation_min_date": data["observed_date"].min().date().isoformat(),
                "observation_max_date": data["observed_date"].max().date().isoformat(),
                "version_id": version,
                "source_sha256": source_hash,
                "parquet_sha256": sha256_file(data_path),
                "row_count_raw": quality["raw_rows"],
                "row_count_valid": quality["valid_rows"],
                "row_count_excluded": quality["excluded_rows"],
                "schema_version": 1,
                "pipeline_version": 1,
                "last_update_status": "manual_unverified",
                "quality": quality,
            }
            (build_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            os.replace(build_dir, version_dir)
        finally:
            if build_dir.exists():
                shutil.rmtree(build_dir)
    else:
        manifest = json.loads((version_dir / "manifest.json").read_text(encoding="utf-8"))
        if manifest["parquet_sha256"] != sha256_file(version_dir / "data.parquet"):
            raise ValueError("El snapshot existente no pasó la verificación de integridad.")
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=root, prefix="current-", suffix=".json", delete=False
    ) as temporary:
        json.dump({"version": version}, temporary)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, pointer)
    return "updated", manifest
