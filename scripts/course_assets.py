#!/usr/bin/env python3
"""코스 표현 자산 생성: 고도 프로파일·타임라인 표·난이도 레이더·요약 카드.
사용: python scripts/course_assets.py --exp hiker --mountain 북한산 [--segments "우이동,백운대"] [--start 09:00] [--access 4 --view 5] [--season "단풍 절정 11/1"]
      파일이 없으면 --sample 로 내장 샘플 코스 사용. data/trails/ 에 산림청 등산로 GeoJSON/GPX 를 넣는다.
"""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import click
from src.common import data_dir, get_logger, set_experiment
from src.media import course_viz as cv
log = get_logger("course_assets")

@click.command()
@click.option("--exp", default=None)
@click.option("--mountain", required=True)
@click.option("--segments", default=None, help="구간 이름 일부를 순서대로, 쉼표 구분")
@click.option("--start", default="09:00")
@click.option("--access", type=int, default=3, help="접근성 1~5 (사람이 판단)")
@click.option("--view", type=int, default=4, help="조망 1~5 (사람이 판단)")
@click.option("--season", default="", help="카드에 넣을 이맘때 문구")
@click.option("--preset", default="standard", type=click.Choice(["basic", "standard", "season", "full"]), help="고도 프로파일 밀도")
@click.option("--layers", default=None, help="레이어 직접 지정 (쉼표): slope_fill,time_axis,markers,hardest,stats,foliage_band,sunset,roundtrip,minimap")
@click.option("--date", "on", default=None, help="산행 날짜 YYYY-MM-DD (단풍 띠·일몰)")
@click.option("--compare", is_flag=True, help="프리셋 4종을 모두 만들어 비교 (profile_<preset>.png)")
@click.option("--sample", is_flag=True, help="파일 없이 내장 샘플 코스로 생성")
@click.option("--dry-run", is_flag=True, help="고도 API 호출 생략")
def main(exp, mountain, segments, start, access, view, season, preset, layers, on, compare, sample, dry_run):
    from datetime import date as _d
    set_experiment(exp)
    course = cv.sample_course() if sample else cv.find_course(mountain, segments.split(",") if segments else None)
    if not course:
        log.error("data/trails/ 에서 '%s' 코스를 찾지 못했습니다. GeoJSON/GPX 를 넣거나 --sample 로 확인하세요", mountain); sys.exit(1)
    out = data_dir() / "assets" / cv.slug(course.mountain)
    on_d = _d.fromisoformat(on) if on else None
    if compare:
        from src.media.profile import render, PRESETS
        cv.ensure_elevation(course, dry_run); out.mkdir(parents=True, exist_ok=True); lon, lat = course.segments[0].coords[0]
        for pname in PRESETS:
            render(course, out / f"profile_{pname}.png", None, pname, start, on_d, lat, lon); log.info("비교용 생성: profile_%s.png", pname)
    res = cv.build_all(course, out, start, access, view, season, dry_run, preset, layers.split(",") if layers else None, on_d)
    log.info("생성: %s", ", ".join(str(res[k]) for k in ["profile", "radar", "card", "area_map", "gpx"]))
    print(res["timeline"])
    print(f"\n초안에 넣을 마크다운:\n![{course.mountain} 고도 프로파일]({res['profile']})\n![{course.mountain} 난이도]({res['radar']})")

if __name__ == "__main__":
    main()
