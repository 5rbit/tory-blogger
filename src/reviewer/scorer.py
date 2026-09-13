"""Claude 품질 채점 (사람이 쓴 것처럼 읽히는가, 경험이 구체적인가)."""
from __future__ import annotations
from src.common import env, get_logger
log = get_logger(__name__)

def score(markdown: str, dry_run: bool = False) -> int:
    if dry_run or not env("ANTHROPIC_API_KEY"):
        log.info("[dry-run] 채점 생략, 8점 가정")
        return 8
    # TODO: REVIEWER_MODEL 로 10점 만점 채점, JSON {"score": n, "reasons": [...]} 응답 파싱
    raise NotImplementedError("채점 연동 예정 (로드맵 3–4주차)")
