"""주간 콘텐츠 캘린더 생성."""
from __future__ import annotations
from dataclasses import asdict
from datetime import date
from src.common import DATA, KeywordCandidate, get_logger, pipeline_config, save_yaml
log = get_logger(__name__)

def assign_types(cands: list[KeywordCandidate], n: int, mix: dict[str, float]) -> list[KeywordCandidate]:
    """점수순 상위 n개에 유형 비율을 배분한다."""
    ranked = sorted(cands, key=lambda c: c.score, reverse=True)[:n]
    slots: list[str] = []
    for t, ratio in mix.items():
        slots += [t] * round(n * ratio)
    slots = (slots + ["info"] * n)[:n]
    for c, t in zip(ranked, slots):
        c.post_type = t
    return ranked

def write_week_plan(cands: list[KeywordCandidate], week: str | None = None) -> str:
    cfg = pipeline_config()
    week = week or date.today().strftime("%Y-W%V")
    plan = assign_types(cands, cfg["schedule"]["posts_per_week"], cfg["content_mix"])
    path = DATA / "keywords" / f"{week}.yaml"
    save_yaml(path, {"week": week, "posts": [asdict(c) for c in plan]})
    log.info("주간 계획 저장: %s (%d편, 승인 대기)", path, len(plan))
    return str(path)
