from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_starts_without_generated_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app_path = Path(__file__).parents[1] / "dashboard" / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=20)

    assert not app.exception
    assert any("No data is available yet" in message.value for message in app.info)
