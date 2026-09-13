#!/usr/bin/env python3
"""사람이 실행: 승인 초안을 네이버 에디터에 채운다. 발행은 사람이 직접."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import click
from src.common import set_experiment
from pathlib import Path
from src.common import get_logger
from src.publisher.editor import fill
from src.distributor.share import distribute
log = get_logger("fill_editor")

@click.command()
@click.argument("draft", type=click.Path(exists=True, path_type=Path))
@click.option("--exp", default=None, help="실험 ID")
@click.option("--dry-run", is_flag=True)
def main(draft, exp, dry_run):
    set_experiment(exp)
    url = fill(draft, dry_run)
    if url:
        log.info("발행 감지: %s", url)
        title = draft.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
        distribute(title, url, summary=title, dry_run=dry_run)
    elif not dry_run:
        log.warning("발행 URL을 감지하지 못했습니다. 발행 후 수동으로 기록하세요")

if __name__ == "__main__":
    main()
