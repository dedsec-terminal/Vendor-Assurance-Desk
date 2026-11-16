"""Build a portable read-only portfolio viewer from verified lab outputs."""
from pathlib import Path
import json
import shutil
from scripts.build_review_reader import build as build_review_reader

ROOT = Path(__file__).resolve().parent
PUBLIC_OUTPUTS = (
    "assessment.json", "results.json", "risk_register.csv", "decision_memo.md",
    "control_review.json", "control_matrix.csv", "unit_validation.json", "browser_validation.json",
    "ciso_entities.png",
    "outcome_scorecard.json", "outcome_scorecard.md", "platform_sync.json",
    "framework_links.json",
)


def build():
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    for name in ("index.html", "app.js", "style.css"):
        shutil.copyfile(ROOT / "web" / name, site / name)
    (site / "output").mkdir(exist_ok=True)
    for name in PUBLIC_OUTPUTS:
        source = ROOT / "output" / name
        if source.exists():
            shutil.copyfile(source, site / "output" / name)
    assessment_path = site / "output/assessment.json"
    assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
    platform_keys = ("name", "status", "version", "upstream_commit", "configuration_executed", "record_counts")
    assessment["platform"] = {k: v for k, v in assessment.get("platform", {}).items() if k in platform_keys}
    assessment_path.write_text(json.dumps(assessment, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")
    build_review_reader()
    print(f"Static portfolio viewer built: {site}")


if __name__ == "__main__":
    build()
