import subprocess
import sys
from pathlib import Path

from tools.validate_spec import validate_spec


def write_spec(directory, requirements, tasks):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "requirements.md").write_text(requirements, encoding="utf-8")
    (directory / "tasks.md").write_text(tasks, encoding="utf-8")


VALID_REQUIREMENTS = """# Requirements

### REQ-001 — One requirement
When called, the system shall act.
"""

VALID_TASKS = """| TASK | Description | REQ | Verification |
|---|---|---|---|
| TASK-001 | Implement it | REQ-001 | Unit test |
"""


def test_accepts_valid_sdd_spec(tmp_path):
    write_spec(tmp_path, VALID_REQUIREMENTS, VALID_TASKS)
    assert validate_spec(tmp_path) == []


def test_reports_unlinked_requirement_unknown_reference_and_missing_task_fields(tmp_path):
    requirements = VALID_REQUIREMENTS + "\n### REQ-002 — Unlinked\n"
    tasks = """| TASK | Description | REQ | Verification |
|---|---|---|---|
| TASK-001 | Missing REQ | | Unit test |
| TASK-002 | Unknown REQ | REQ-999 | - |
"""
    write_spec(tmp_path, requirements, tasks)

    errors = validate_spec(tmp_path)

    assert "TASK-001: no REQ reference" in errors
    assert "TASK-002: references unknown REQ-999" in errors
    assert "TASK-002: verification is empty" in errors
    assert "REQ-001: no task references this requirement" in errors
    assert "REQ-002: no task references this requirement" in errors


def test_reports_missing_documents_without_raising(tmp_path):
    errors = validate_spec(tmp_path)
    assert len(errors) == 2
    assert any(error.startswith("requirements.md: cannot read file") for error in errors)
    assert any(error.startswith("tasks.md: cannot read file") for error in errors)


def test_cli_returns_nonzero_for_invalid_spec_and_zero_for_valid_spec(tmp_path):
    write_spec(tmp_path, VALID_REQUIREMENTS, VALID_TASKS)
    script = str(Path(__file__).parents[2] / "tools" / "validate_spec.py")

    valid = subprocess.run([sys.executable, script, str(tmp_path)], capture_output=True, text=True, check=False)
    assert valid.returncode == 0
    assert "Spec SDD válida" in valid.stdout

    (tmp_path / "tasks.md").write_text("not a task table\n", encoding="utf-8")
    invalid = subprocess.run([sys.executable, script, str(tmp_path)], capture_output=True, text=True, check=False)
    assert invalid.returncode == 1
    assert "no TASK-NNN rows" in invalid.stderr
