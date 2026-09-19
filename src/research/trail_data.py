"""공공데이터포털 — 전국등산로표준데이터 / 산림청 산정보 서비스. 코스 표(거리·시간·난이도) 초안용.
- 전국등산로표준데이터: https://www.data.go.kr/data/15029184/standard.do  (CSV/OpenAPI)
- 산림청 산정보: https://www.data.go.kr/data/15058662/openapi.do  (100대 명산 코스·볼거리)
.env: DATA_GO_KR_KEY
"""
from __future__ import annotations
from src.common import env, get_logger
log = get_logger(__name__)

def course_info(mountain: str, dry_run: bool = False) -> list[dict]:
    """산 이름 → [{course, distance_km, minutes, difficulty, trailhead}] (초안 표에 채움)."""
    if dry_run or not env("DATA_GO_KR_KEY"):
        log.info("[dry-run] 등산로 공공데이터 생략: %s", mountain)
        return []
    # TODO: 전국등산로표준데이터 OpenAPI 호출 (serviceKey=DATA_GO_KR_KEY, 산 이름 필터)
    raise NotImplementedError("등산로 공공데이터 연동 예정 (로드맵 1–2주차)")
