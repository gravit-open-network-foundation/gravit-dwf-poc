import json
from pathlib import Path

from scenarios.run import main


def test_outcomes():
    assert main() == 0
    rows = json.loads((Path(__file__).resolve().parent.parent / "results" / "decisions.json").read_text())
    assert [r["outcome"] for r in rows] == ["APPROVED"] + ["REJECTED"] * 6
