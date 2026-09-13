"""Claude로 네이버 스타일 초안 생성."""
from __future__ import annotations
from src.common import TEMPLATES, KeywordCandidate, env, get_logger, pipeline_config
log = get_logger(__name__)

SYSTEM = """당신은 네이버 블로그 IT·테크 분야 작성자입니다.
- 직접 경험 문장("직접 해보니", "제 경우에는")을 3개 이상 넣는다
- 사진 슬롯을 [사진: 설명] 형식으로 5개 이상 넣는다
- 외부 링크는 넣지 않는다
- 광고성·낚시성 표현 금지, 소제목은 ## 로 3개 이상
- 마지막 줄에 해시태그 5~10개"""

def load_template(post_type: str) -> str:
    return (TEMPLATES / f"{post_type}.md").read_text(encoding="utf-8")

def generate_draft(kw: KeywordCandidate, dry_run: bool = False) -> str:
    template = load_template(kw.post_type)
    if dry_run or not env("ANTHROPIC_API_KEY"):
        log.info("[dry-run] Claude 생성 생략, 템플릿 반환: %s", kw.keyword)
        return template.replace("{keyword}", kw.keyword)
    # TODO: anthropic.Anthropic().messages.create(model=cfg['models']['writer'], system=SYSTEM,
    #       messages=[{"role":"user","content": template.replace('{keyword}', kw.keyword)}])
    raise NotImplementedError("Claude 생성 연동 예정 (로드맵 3–4주차)")
