"""발행 후 배포: X/Threads 요약, 뉴스레터 큐, 서치어드바이저 체크리스트."""
from __future__ import annotations
from src.common import data_dir, get_logger
log = get_logger(__name__)

def distribute(title: str, url: str, summary: str, dry_run: bool = False) -> None:
    if dry_run:
        log.info("[dry-run] 배포 생략: %s", title)
        return
    # TODO: X API v2 POST /2/tweets, Threads API
    queue = data_dir() / "reports" / "newsletter_queue.md"
    with open(queue, "a", encoding="utf-8") as f:
        f.write(f"- [{title}]({url}) — {summary}\n")
    log.info("뉴스레터 큐 적재. 서치어드바이저(https://searchadvisor.naver.com) 수집 요청을 확인하세요.")
