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
    assert app.button[0].label == "Cambiar a modo oscuro"

    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["appearance"] == "Oscuro"
    assert app.button[0].label == "Cambiar a modo claro"
    assert any("--fs-background:#121417" in item.value for item in app.markdown)
