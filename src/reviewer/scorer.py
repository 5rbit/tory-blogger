"""Claude Code CLI로 품질 채점 (사람이 쓴 것처럼 읽히는가, 경험이 구체적인가)."""
from __future__ import annotations
from src import claude_cli
from src.common import get_logger, pipeline_config
log = get_logger(__name__)

SYSTEM = "당신은 네이버 블로그 품질 심사자입니다. AI 티가 나거나 경험이 추상적이면 낮은 점수를 주세요."

def score(markdown: str, dry_run: bool = False) -> tuple[int, list[str]]:
    if dry_run or not claude_cli.available():
        log.info("[dry-run] 채점 생략, 8점 가정")
        return 8, []
    prompt = ("다음 글을 10점 만점으로 채점하세요. 기준: 사람이 쓴 듯한 자연스러움, 경험의 구체성, "
              "소제목 구조, 광고성 없음.\n형식: {\"score\": 정수, \"reasons\": [\"문제점\", ...]}\n\n" + markdown)
    data = claude_cli.ask_json(prompt, SYSTEM, pipeline_config()["models"]["reviewer"])
    return int(data.get("score", 0)), list(data.get("reasons", []))
