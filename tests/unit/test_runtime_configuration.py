import json
import os
import shutil
import subprocess
import sys
import tomllib
from types import ModuleType
from pathlib import Path

import pytest
from sqlmodel import Session

from investiq.data.database import create_db, database_url, make_engine
from investiq.data.models import Instrument
from investiq.ml import pipeline
from investiq.settings import get_settings
from investiq.legacy_ui import main as legacy_main


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


@pytest.mark.parametrize("launcher_name,arguments,invocation", [
    ("run_web.sh", ["--port", "8900", "argument with spaces"], ["-m", "investiq.web.server"]),
    ("run_streamlit.sh", ["--server.port", "8900", "--", "argument with spaces"],
     ["-m", "streamlit", "run", "src/investiq/app.py"]),
])
def test_launcher_resolves_repo_and_honors_python_override(tmp_path, launcher_name, arguments, invocation):
    repository = tmp_path / "repository with spaces"
    repository.mkdir()
    launcher = repository / launcher_name
    source_launcher = Path(__file__).resolve().parents[2] / launcher_name
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
        ["bash", str(launcher), *arguments],
        cwd=caller_directory,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout == result.stderr == ""
    if launcher_name == "run_streamlit.sh":
        invocation = [*invocation[:-1], str(repository / invocation[-1])]
    assert capture_file.read_text(encoding="utf-8").splitlines() == [str(repository.resolve()), *invocation, *arguments]


def test_default_web_entrypoint_does_not_require_streamlit(tmp_path):
    repository = Path(__file__).resolve().parents[2]
    configuration = tomllib.loads((repository / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert not any(requirement.casefold().startswith("streamlit") for requirement in configuration["dependencies"])
    assert any(requirement.casefold().startswith("streamlit") for requirement in configuration["optional-dependencies"]["legacy-ui"])
    assert not any(requirement.casefold().startswith("streamlit") for requirement in configuration["optional-dependencies"]["dev"])
    entry = configuration["scripts"]["investiq-app"]
    assert entry == configuration["scripts"]["investiq-web"]
    program = '''
import importlib
import importlib.abc
import sys

class WithoutStreamlit(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "streamlit" or fullname.startswith("streamlit."):
            raise ModuleNotFoundError("Streamlit is not installed", name=fullname)

sys.meta_path.insert(0, WithoutStreamlit())
module, function = sys.argv[1].split(":", 1)
sys.argv = ["investiq-app", "--help"]
getattr(importlib.import_module(module), function)()
'''
    environment = {
        **os.environ,
        "PYTHONPATH": str(repository / "src"),
        "NVIDIA_API_KEY": "", "TWELVE_DATA_API_KEY": "", "MARKETAUX_API_KEY": "", "SEC_USER_AGENT": "",
    }
    result = subprocess.run([sys.executable, "-c", program, entry], cwd=tmp_path, env=environment,
                            capture_output=True, text=True, check=True)
    assert "--port" in result.stdout and "InvestiQ" in result.stdout
    assert not (tmp_path / "investiq.db").exists()


def test_legacy_launcher_explains_missing_optional_dependency(tmp_path):
    interpreter = tmp_path / "without streamlit"
    interpreter.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    interpreter.chmod(0o755)
    launcher = Path(__file__).resolve().parents[2] / "run_streamlit.sh"
    result = subprocess.run(["bash", str(launcher)], cwd=tmp_path,
                            env={**os.environ, "INVESTIQ_PYTHON": str(interpreter)},
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert "bash run_web.sh" in result.stderr
    assert ".[legacy-ui]" in result.stderr
    assert "Traceback" not in result.stderr


def test_explicit_legacy_cli_starts_streamlit_server_instead_of_bare_ui(monkeypatch):
    # These modules stand in for the optional dependency even when it is absent.
    streamlit = ModuleType("streamlit")
    web = ModuleType("streamlit.web")
    cli = ModuleType("streamlit.web.cli")
    calls = []

    def start_server():
        calls.append(list(sys.argv))
        return 0

    cli.main = start_server
    streamlit.web = web
    web.cli = cli
    for module in (streamlit, web, cli):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    previous_argv = sys.argv

    assert legacy_main(["--server.port", "8888"]) == 0

    app_file = Path(__file__).resolve().parents[2] / "src/investiq/app.py"
    assert calls == [["streamlit", "run", str(app_file), "--server.port", "8888"]]
    assert sys.argv is previous_argv


def test_legacy_cli_explains_missing_extra_without_traceback(monkeypatch, capsys):
    import builtins

    original_import = builtins.__import__

    def without_streamlit(name, *args, **kwargs):
        if name == "streamlit" or name.startswith("streamlit."):
            raise ModuleNotFoundError("Optional Streamlit unavailable", name="streamlit")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_streamlit)

    assert legacy_main([]) == 1
    shown = capsys.readouterr()
    assert "investiq-app" in shown.err and ".[legacy-ui]" in shown.err
    assert "Traceback" not in shown.err
