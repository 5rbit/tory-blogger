#!/usr/bin/env python3
"""실험 간 주간 비교표: 발행 수, 검수 통과율, 방문자(리포트 CSV가 있으면), 비용. 승자·중단 판단용."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import click
from src.common import DATA, EXPERIMENTS, list_experiments, load_yaml, set_experiment, data_dir, pipeline_config

def stats(exp: str) -> dict:
    set_experiment(exp)
    d = data_dir(); cfg = pipeline_config()
    posts = [p for y in (d / "keywords").glob("*.yaml") for p in load_yaml(y).get("posts", [])] if (d / "keywords").exists() else []
    status = {s: sum(1 for p in posts if p["status"] == s) for s in ["pending", "approved", "drafted", "published", "rejected"]}
    return {"실험": exp, "주제": cfg["topic"]["main"], "계획": len(posts), **status,
            "초안": len(list((d / "drafts").glob("*.md"))) if (d / "drafts").exists() else 0,
            "월비용": cfg.get("cost_per_month", 0)}

@click.command()
def main():
    rows = [stats(e) for e in list_experiments()]
    if not rows:
        print("실험이 없습니다"); return
    keys = list(rows[0].keys())
    print("| " + " | ".join(keys) + " |"); print("|" + "---|" * len(keys))
    for r in rows:
        print("| " + " | ".join(str(r[k]) for k in keys) + " |")

if __name__ == "__main__":
    main()
