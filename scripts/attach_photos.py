#!/usr/bin/env python3
"""초안의 [사진: ...] 슬롯을 포토코리아(공공누리 1유형) 사진으로 채운다. 출처 캡션 자동 삽입.
사용: python scripts/attach_photos.py --exp hiker <초안.md> --keyword 북한산 [--month 10]
"""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datetime import date
import click
from src.common import get_logger, set_experiment
from src.media.photos import search, fill_slots
log = get_logger("attach_photos")

@click.command()
@click.argument("draft", type=click.Path(exists=True, path_type=Path))
@click.option("--exp", default=None)
@click.option("--keyword", required=True, help="검색어 (산 이름·지명)")
@click.option("--month", type=int, default=None, help="이맘때 우선 정렬 (기본: 다음 달)")
@click.option("--dry-run", is_flag=True)
def main(draft, exp, keyword, month, dry_run):
    set_experiment(exp)
    month = month or (date.today().month % 12 + 1)
    text = draft.read_text(encoding="utf-8")
    photos = search(keyword, month=month, limit=text.count("[사진:"), dry_run=dry_run)
    new, n = fill_slots(text, photos)
    log.info("슬롯 %d개 중 %d개 채움 (키워드 %s, %d월 우선)", text.count("[사진:"), n, keyword, month)
    if dry_run:
        print(new[:1200])
    else:
        draft.write_text(new, encoding="utf-8")

if __name__ == "__main__":
    main()
