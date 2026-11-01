"""Valida enlaces mínimos entre requisitos, tareas y verificaciones SDD."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQ_ID = re.compile(r"\bREQ-\d{3}\b")
TASK_ID = re.compile(r"^TASK-\d{3}$")
REQ_HEADING = re.compile(r"^\s*###\s+(REQ-\d{3})\b", re.MULTILINE)
PLACEHOLDERS = {"", "-", "—", "todo", "tbd", "n/a", "<...>"}


def _task_rows(contents: str) -> list[tuple[str, str, str]]:
    """Return task id, REQ cell, and verification cell from Markdown table rows."""
    rows = []
    for line in contents.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or not TASK_ID.fullmatch(cells[0]):
            continue
        req_cell = cells[2] if len(cells) > 2 else ""
        verification_cell = cells[3] if len(cells) > 3 else ""
        rows.append((cells[0], req_cell, verification_cell))
    return rows


def validate_spec(spec_dir: str | Path) -> list[str]:
    """Return deterministic, human-readable errors for a feature spec directory."""
    directory = Path(spec_dir)
    requirements_path = directory / "requirements.md"
    tasks_path = directory / "tasks.md"
    errors: list[str] = []

    requirements_text = None
    tasks_text = None
    for path, label in ((requirements_path, "requirements.md"), (tasks_path, "tasks.md")):
        try:
            contents = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{label}: cannot read file ({exc.strerror or exc})")
            continue
        if label == "requirements.md":
            requirements_text = contents
        else:
            tasks_text = contents

    if requirements_text is None or tasks_text is None:
        return errors

    requirements = set(REQ_HEADING.findall(requirements_text))
    task_rows = _task_rows(tasks_text)
    if not requirements:
        errors.append("requirements.md: no REQ-NNN headings found")
    if not task_rows:
        errors.append("tasks.md: no TASK-NNN rows found in the task table")

    linked_requirements: set[str] = set()
    for task_id, req_cell, verification_cell in task_rows:
        referenced = REQ_ID.findall(req_cell)
        if not referenced:
            errors.append(f"{task_id}: no REQ reference")
        for req_id in referenced:
            if req_id not in requirements:
                errors.append(f"{task_id}: references unknown {req_id}")
            else:
                linked_requirements.add(req_id)
        if verification_cell.strip().casefold() in PLACEHOLDERS:
            errors.append(f"{task_id}: verification is empty")

    for req_id in sorted(requirements - linked_requirements):
        errors.append(f"{req_id}: no task references this requirement")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec_dir", type=Path, help="directorio con requirements.md y tasks.md")
    args = parser.parse_args(argv)

    errors = validate_spec(args.spec_dir)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Spec SDD válida: {args.spec_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
