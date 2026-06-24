import json
import subprocess
import sys
from pathlib import Path

GEN = Path("skills/visual-ux-review/scripts/generate_report.py")

def _run(tmp_path: Path, data: dict) -> Path:
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    subprocess.run(
        [sys.executable, str(GEN), "--findings", str(findings),
         "--out-dir", str(out), "--format", "md,html"],
        check=True,
    )
    return out

def _data(**extra) -> dict:
    return {"title": "T", "url": "http://x", "timestamp": "2026-06-24",
            "screenshots": {}, "findings": [], **extra}

def test_driver_rendered_when_present(tmp_path):
    out = _run(tmp_path, _data(driver="playwright-mcp"))
    assert "playwright-mcp" in (out / "report.md").read_text(encoding="utf-8")
    assert "playwright-mcp" in (out / "report.html").read_text(encoding="utf-8")

def test_no_driver_is_backcompat(tmp_path):
    out = _run(tmp_path, _data())  # no driver key
    assert (out / "report.md").exists()  # still generates, no crash
