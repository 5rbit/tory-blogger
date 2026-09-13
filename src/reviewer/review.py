from __future__ import annotations
from src.common import get_logger, pipeline_config
from src.reviewer import rules, similarity, scorer
log = get_logger(__name__)

def review(markdown: str, title: str, dry_run: bool = False) -> tuple[bool, list[str]]:
    cfg = pipeline_config()["review"]
    problems = [f"{r.name} 미달 ({r.detail})" for r in rules.check(markdown, title) if not r.passed]
    sim = similarity.max_similarity(markdown)
    if sim > cfg["max_similarity"]:
        problems.append(f"유사도 초과 ({sim:.0%})")
    s = scorer.score(markdown, dry_run)
    if s < cfg["min_score"]:
        problems.append(f"품질 점수 미달 ({s}/10)")
    for p in problems:
        log.warning("검수: %s", p)
    return (not problems, problems)
