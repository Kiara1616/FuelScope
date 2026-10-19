"""Comprueba que el snapshot histórico distribuido sea legible e íntegro."""

from pathlib import Path

from fuelscope.snapshot import read_snapshot


def test_bundled_snapshot_matches_audited_source():
    root = Path(__file__).resolve().parents[1] / "data" / "processed"
    data, manifest = read_snapshot(root)
    assert manifest["source_sha256"] == (
        "a733b48f6ff24d1e0837b622c1ec472cc2bb2924dcb2a90b145a77e1d4262eaa"
    )
    assert len(data) == manifest["row_count_valid"] == 1_061_899
    assert manifest["observation_min_date"] == "2026-01-01"
    assert manifest["observation_max_date"] == "2026-02-28"
    assert "department" not in data.columns
