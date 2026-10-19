"""Valida una nueva descarga oficial antes de actualizar el snapshot versionado."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from fuelscope.data import normalize_wide, read_csv_bytes
from fuelscope.snapshot import publish_snapshot, read_snapshot, sha256_file

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data" / "source_contract.json"
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
STATUS_PATH = ROOT / "data" / "source_status.json"
CSV_ARCHIVE = RAW_DIR / "precios_combustibles_anonimizados_20260301_part1.csv.gz"
EXPECTED_COLUMNS = [
    "fecha_emision",
    "fecha_corte",
    "id",
    "fe_eval",
    "g_premium",
    "g_regular",
    "diesel",
    "gnv",
    "glp_g",
    "glp_e",
    "ANON_CO_LOCAL_VENTA",
]
PINNED_DOCUMENTS = {
    "dictionary": "dbfb913f27707595959207c1691c1e7f83c0b5de0720c18461b6ade7e07e55a2",
    "metadata": "f55e77766b5e88197c52528bb57a68fa2dc3f9543aa45c17fa93288bb2739303",
}


def validate_source(csv_path: Path, contract: dict, previous: dict | None) -> dict:
    if csv_path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("El CSV supera el límite de 50 MB.")
    frame = read_csv_bytes(csv_path.read_bytes())
    if frame.columns.tolist() != EXPECTED_COLUMNS:
        raise ValueError("El esquema oficial cambió; se requiere revisión manual.")
    observed = pd.to_datetime(frame["fe_eval"].astype("string"), format="%Y%m%d", errors="coerce")
    if observed.isna().any():
        raise ValueError("El CSV contiene fechas FE_EVAL inválidas.")
    data, quality = normalize_wide(
        frame,
        contract["mapping"],
        contract["price_columns"],
        contract["units"],
    )
    if data.empty:
        raise ValueError("El CSV nuevo no contiene precios válidos.")
    maximum = data["observed_date"].max().date().isoformat()
    if previous is not None:
        if maximum < previous["observation_max_date"]:
            raise ValueError("El CSV nuevo retrocede la fecha máxima observada.")
        if len(data) < previous["row_count_valid"] // 2:
            raise ValueError("El CSV nuevo pierde más de la mitad de las observaciones válidas.")
    return {
        "quality": quality,
        "min_date": data["observed_date"].min().date().isoformat(),
        "max_date": maximum,
    }


def refresh(csv_path: Path, dictionary_path: Path, metadata_path: Path) -> str:
    document_paths = {"dictionary": dictionary_path, "metadata": metadata_path}
    for name, path in document_paths.items():
        if sha256_file(path) != PINNED_DOCUMENTS[name]:
            raise ValueError(f"El archivo {name} cambió; se requiere revisar el contrato.")
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    existing = read_snapshot(PROCESSED_DIR)
    previous = existing[1] if existing is not None else None
    source_hash = sha256_file(csv_path)
    if previous is not None and source_hash == previous["source_sha256"] and STATUS_PATH.exists():
        return "no_change"
    audit = validate_source(csv_path, contract, previous)
    status, manifest = publish_snapshot(
        csv_path,
        PROCESSED_DIR,
        contract["mapping"],
        contract["units"],
        contract["source_url"],
        contract["license"],
        contract["price_columns"],
    )
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=RAW_DIR, prefix="source-", suffix=".gz", delete=False
    ) as temp:
        temp_path = Path(temp.name)
        with (
            csv_path.open("rb") as source,
            gzip.GzipFile(
                filename="", mode="wb", fileobj=temp, mtime=0, compresslevel=9
            ) as archive,
        ):
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                archive.write(chunk)
    os.replace(temp_path, CSV_ARCHIVE)
    source_status = {
        "source_url": contract["source_url"],
        "download_url": contract["resource_urls"]["csv"],
        "source_sha256": source_hash,
        "dictionary_sha256": PINNED_DOCUMENTS["dictionary"],
        "metadata_sha256": PINNED_DOCUMENTS["metadata"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_version": manifest["version_id"],
        "observation_min_date": audit["min_date"],
        "observation_max_date": audit["max_date"],
        "source_rows": audit["quality"]["source_rows"],
        "valid_prices": audit["quality"]["valid_rows"],
    }
    STATUS_PATH.write_text(
        json.dumps(source_status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--dictionary", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    args = parser.parse_args()
    print(refresh(args.csv, args.dictionary, args.metadata))


if __name__ == "__main__":
    main()
