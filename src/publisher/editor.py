"""Playwright로 네이버 SmartEditor ONE을 채운다. 발행 버튼은 절대 자동 클릭하지 않는다."""
from __future__ import annotations
import time
from pathlib import Path
from src.common import CONFIG, current_experiment, env, get_logger, load_yaml, pipeline_config
log = get_logger(__name__)
def profile_dir() -> Path:
    return Path.home() / ".tory-blogger" / "browser" / (current_experiment() or "default")

def parse_draft(path: Path) -> tuple[str, str, list[str]]:
    """초안 첫 줄(# 제목), 본문, 해시태그를 분리한다."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else ""
    tags = [w.lstrip("#") for w in text.split() if w.startswith("#") and len(w) > 1 and not w.startswith("##")]
    body = "\n".join(l for l in lines[1:] if not l.strip().startswith("#") or l.startswith("##"))
    return title, body, tags

def fill(draft: Path, dry_run: bool = False) -> str | None:
    title, body, tags = parse_draft(draft)
    log.info("초안 파싱: 제목=%r, 본문 %d자, 태그 %d개", title, len(body), len(tags))
    if dry_run:
        log.info("[dry-run] 브라우저 실행 생략")
        return None
    sel = load_yaml(CONFIG / "selectors.yaml")["editor"]
    blog_id = pipeline_config().get("blog_id") or env("NAVER_BLOG_ID")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(profile_dir()), headless=False)
        page = ctx.new_page()
        page.goto(sel["write_url"].format(blog_id=blog_id))
        # TODO: 로그인 안 된 경우 사람이 로그인할 때까지 대기
        page.click(sel["title"]); page.keyboard.type(title, delay=30)
        page.click(sel["body"])
        for para in body.split("\n\n"):
            page.keyboard.type(para, delay=15); page.keyboard.press("Enter"); time.sleep(0.8)
        # TODO: 태그 입력, [사진: ...] 슬롯 강조 표시
        log.info("에디터 채움 완료. 사진을 첨부하고 발행 버튼을 직접 누르세요.")
        url = _wait_for_publish(page, sel, blog_id)
        ctx.close()
    return url

def _wait_for_publish(page, sel, blog_id, timeout_s: int = 1800) -> str | None:
    import re
    pat = re.compile(sel["published_url_pattern"].format(blog_id=blog_id))
    for _ in range(timeout_s):
        if pat.search(page.url):
            return page.url
        time.sleep(1)
    return None
