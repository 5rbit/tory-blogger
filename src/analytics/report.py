"""블로그 통계·애드포스트 CSV(사람이 내보낸 파일)를 주간 리포트로 만든다."""
from __future__ import annotations
from datetime import date
from src.common import DATA, get_logger
log = get_logger(__name__)

def build_report(week: str | None = None, dry_run: bool = False) -> str:
    week = week or date.today().strftime("%Y-W%V")
    raw = sorted((DATA / "reports" / "raw").glob("*.csv"))
    out = DATA / "reports" / f"{week}.md"
    lines = [f"# 주간 리포트 {week}", "", f"원본 파일 {len(raw)}개", ""]
    # TODO: 통계 CSV 파싱 → 방문자·유입 키워드·체류 시간 표, 애드포스트 수익, Claude 개선 제안
    if not dry_run:
        out.write_text("\n".join(lines), encoding="utf-8")
    log.info("리포트: %s", out)
    return str(out)
