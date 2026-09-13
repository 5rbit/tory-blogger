#!/usr/bin/env python3
"""매일 새벽: 승인 키워드 1개 → 초안 생성 → 검수 → data/drafts."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import click
from datetime import date
from src.common import DATA, KeywordCandidate, get_logger, load_yaml, pipeline_config, save_yaml
from src.writer.generate import generate_draft
from src.reviewer.review import review
log = get_logger("daily_draft")

def next_approved():
    for p in sorted((DATA / "keywords").glob("*.yaml"), reverse=True):
        plan = load_yaml(p)
        for post in plan["posts"]:
            if post["status"] == "approved":
                return p, plan, post
    return None, None, None

@click.command()
@click.option("--dry-run", is_flag=True)
def main(dry_run):
    path, plan, post = next_approved()
    if not post:
        if dry_run:
            log.info("[dry-run] 승인 키워드 없음 → 샘플 키워드로 진행")
            post = {"keyword": "샘플 키워드", "post_type": "info", "status": "approved"}
        else:
            log.info("승인된 키워드가 없습니다. 종료"); return
    kw = KeywordCandidate(**{k: v for k, v in post.items() if k in KeywordCandidate.__dataclass_fields__})
    max_regen = pipeline_config()["review"]["max_regenerations"]
    problems = []
    for attempt in range(max_regen + 1):
        log.info("초안 생성 (%d/%d): %s", attempt + 1, max_regen + 1, kw.keyword)
        md = generate_draft(kw, dry_run, feedback=problems or None)
        ok, problems = review(md, kw.keyword, dry_run)
        if ok or dry_run:
            break
    out = DATA / "drafts" / f"{date.today():%Y%m%d}-{kw.keyword.replace(' ', '_')}.md"
    if not dry_run:
        out.write_text(md, encoding="utf-8")
        post["status"] = "drafted"; save_yaml(path, plan)
    log.info("초안 저장: %s (검수 %s, 문제 %d건)", out, "통과" if ok else "미달", len(problems))

if __name__ == "__main__":
    main()
