import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from sqlmodel import Session

from investiq.data.database import create_db, database_url, make_engine
from investiq.data.models import Instrument
from investiq.ml import pipeline
from investiq.settings import get_settings


@pytest.mark.parametrize("override_environment", [False, True])
def test_train_cli_shares_app_database_settings(tmp_path, monkeypatch, capsys, override_environment):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    file_database = tmp_path / "configured by dotenv.db"
    (tmp_path / ".env").write_text(f'DATABASE_URL="sqlite:///{file_database}"\n', encoding="utf-8")
    expected_database = file_database
    if override_environment:
        expected_database = tmp_path / "environment override.db"
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{expected_database}")

    # Use the same Settings/engine construction as the app and persist a marker.
    app_settings = get_settings()
    assert database_url() == app_settings.database_url == f"sqlite:///{expected_database}"
    app_engine = create_db(make_engine(app_settings.database_url))
    with Session(app_engine) as session:
        session.add(Instrument(symbol="CONFIG", name="Configuration marker", kind="ETF", sector="test"))
        session.commit()
    app_engine.dispose()

    calls = []

    def fake_training(session, *, artifact_dir, seed):
        assert session.get(Instrument, "CONFIG") is not None
        calls.append((session.get_bind().url.database, artifact_dir, seed))
        return {"configuration": "verified"}

    def unexpected_ingest(*args, **kwargs):
        pytest.fail("The train command must not ingest or contact a data provider")

    monkeypatch.setattr(pipeline, "run_training", fake_training)
    monkeypatch.setattr(pipeline, "run_ingest", unexpected_ingest)
    monkeypatch.setattr(sys, "argv", ["investiq-data", "train", "--artifact-dir", "local artifacts", "--seed", "7"])

    pipeline.main()

    assert calls == [(str(expected_database), "local artifacts", 7)]
    assert json.loads(capsys.readouterr().out) == {"configuration": "verified"}
    if override_environment:
        assert not file_database.exists()


def test_launcher_resolves_repo_and_honors_python_override(tmp_path):
    repository = tmp_path / "repository with spaces"
    repository.mkdir()
    launcher = repository / "run_streamlit.sh"
    source_launcher = Path(__file__).resolve().parents[2] / "run_streamlit.sh"
    shutil.copyfile(source_launcher, launcher)
    local_python = repository / ".venv" / "bin" / "python"
    local_python.parent.mkdir(parents=True)
    local_python.write_text("#!/bin/sh\nexit 91\n", encoding="utf-8")
    local_python.chmod(0o755)

    override_python = tmp_path / "custom Python executable"
    override_python.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@" > "$CAPTURE_FILE"\n', encoding="utf-8")
    override_python.chmod(0o755)
    capture_file = tmp_path / "captured arguments.txt"
    caller_directory = tmp_path / "another working directory"
    caller_directory.mkdir()
    environment = {
        **os.environ,
        "INVESTIQ_PYTHON": str(override_python),
        "CAPTURE_FILE": str(capture_file),
    }

    result = subprocess.run(
        ["bash", str(launcher), "--server.port", "8900", "--", "argument with spaces"],
        cwd=caller_directory,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout == result.stderr == ""
    assert capture_file.read_text(encoding="utf-8").splitlines() == [
        str(repository.resolve()),
        "-m",
        "streamlit",
        "run",
        str(repository / "src" / "investiq" / "app.py"),
        "--server.port",
        "8900",
        "--",
        "argument with spaces",
    ]
