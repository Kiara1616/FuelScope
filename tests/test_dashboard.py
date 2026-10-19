"""Comprueba la vista inicial y el límite real del calendario."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_snapshot_dashboard_starts_with_bounded_dates():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=120)
    app.run()

    assert not app.exception
    assert len(app.get("plotly_chart")) == 2
    assert app.date_input[0].proto.min == "2026-01-01"
    assert app.date_input[0].proto.max == "2026-02-28"
