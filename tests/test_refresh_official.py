"""Evita publicar silenciosamente un esquema distinto del recurso conocido."""

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.refresh_official import CONTRACT_PATH, EXPECTED_COLUMNS, validate_source


def test_changed_official_schema_requires_review(tmp_path):
    csv_path = tmp_path / "new.csv"
    pd.DataFrame({column: [1] for column in EXPECTED_COLUMNS[:-1]}).to_csv(csv_path, index=False)
    contract = json.loads(Path(CONTRACT_PATH).read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="esquema oficial cambió"):
        validate_source(csv_path, contract, None)
