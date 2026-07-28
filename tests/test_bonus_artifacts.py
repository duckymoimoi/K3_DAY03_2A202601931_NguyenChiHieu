from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bonus_scorecard_documents_bonus_paths():
    scorecard = ROOT / "artifacts/bonus/bonus_scorecard.md"
    if not scorecard.exists():
        return

    text = scorecard.read_text(encoding="utf-8")
    assert "Extra Monitoring" in text
    assert "Live System Demo" in text
    assert "Failure Handling" in text
