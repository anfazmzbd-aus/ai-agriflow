"""Verify positive typing and exact expected negative diagnostic locations."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from mypy import api


@pytest.mark.parametrize("filename", ["workflows_contracts.py", "workflows_contracts_invalid.py"])
def test_public_contracts_with_mypy(filename: str, tmp_path: Path) -> None:
    """Expected static errors must match marked lines and diagnostic codes exactly."""
    tests = Path(__file__).resolve().parents[2]
    fixture = tests / "typing" / filename
    stdout, stderr, exit_code = api.run(
        [
            "--no-incremental",
            "--show-error-codes",
            "--no-pretty",
            "--no-error-summary",
            "--cache-dir",
            str(tmp_path / "mypy"),
            "--config-file",
            str(tests.parent / "pyproject.toml"),
            str(fixture),
        ]
    )
    expected = []
    for line_number, line in enumerate(fixture.read_text(encoding="utf-8").splitlines(), start=1):
        if "# reject: " in line:
            expected.append((line_number, line.split("# reject: ", 1)[1]))
    diagnostics = re.findall(r"^(.+):(\d+): error: .*\[([\w-]+)\]$", stdout, re.MULTILINE)
    assert all(Path(path).resolve() == fixture.resolve() for path, _, _ in diagnostics), stdout
    actual = [(int(line), code) for _, line, code in diagnostics]
    assert stderr == ""
    assert actual == expected, stdout
    assert exit_code == (1 if expected else 0), stdout
