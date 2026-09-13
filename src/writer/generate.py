"""Claude Code CLI로 네이버 스타일 초안 생성 (API 키 불필요)."""
from __future__ import annotations
from src import claude_cli
from src.common import TEMPLATES, KeywordCandidate, get_logger, pipeline_config
log = get_logger(__name__)

SYSTEM = """당신은 네이버 블로그 IT·테크 분야 작성자입니다. 아래 규칙을 반드시 지키세요.
- 첫 줄은 '# 제목' (30자 이내, 키워드 앞쪽)
- 공백 제외 1,500자 이상, '## ' 소제목 3개 이상, 각 소제목 아래 200자 이상
- 직접 경험 문장("직접 해보니", "제 경우에는", "써보니")을 3개 이상
- 사진 슬롯을 [사진: 설명] 형식으로 5개 이상
- 외부 링크(URL) 금지, 광고성·낚시성 표현 금지
- 마지막 줄에 해시태그 5~10개
- Markdown 본문만 출력. 설명이나 인사말 없이."""

def load_template(post_type: str) -> str:
    return (TEMPLATES / f"{post_type}.md").read_text(encoding="utf-8")

def generate_draft(kw: KeywordCandidate, dry_run: bool = False, feedback: list[str] | None = None) -> str:
    template = load_template(kw.post_type).replace("{keyword}", kw.keyword)
    if dry_run or not claude_cli.available():
        log.info("[dry-run] 생성 생략, 템플릿 반환: %s", kw.keyword)
        return template
    prompt = f"키워드: {kw.keyword}\n유형: {kw.post_type}\n관점: {kw.angle or '없음'}\n\n아래 구조를 따라 글을 완성하세요.\n\n{template}"
    if feedback:
        prompt += "\n\n이전 초안의 문제점을 고치세요:\n- " + "\n- ".join(feedback)
    return claude_cli.ask(prompt, SYSTEM, pipeline_config()["models"]["writer"])
