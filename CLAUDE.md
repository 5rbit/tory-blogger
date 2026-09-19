# tory-blogger

네이버 블로그 수익화 프로젝트. 페르소나: 주 2~3회 산에 가는 디지털 노마드 등산 블로거 (`experiments/hiker`).

- 글 표준: 한줄요약 → 코스 표 → 이맘때 근거 → 구간별 실측·사진 → 지도 링크 → 그날 쓴 용품 1개(쇼핑커넥트) → 하산 후 맛집 표 → 주의사항
- 사진은 한국관광공사 포토코리아(공공누리 1유형, 출처 캡션 필수). 타인 블로그 사진 금지, KorService2 사진(3유형)은 변경 금지

- 문서는 기술 용어를 제외하고 모두 한글로 작성
- 네이버 블로그는 공식 글쓰기 API가 없다. 발행은 **반자동**(초안·에디터 채우기까지 자동, 발행 클릭은 사람)
- 완전 자동 발행, 대량 발행, 복붙 글은 금지 (검색 누락·계정 제재 위험)
- 계획 문서: `docs/` (01 전략 → 02 자동화 → 03 로드맵/KPI)
- 실험(블로그)은 `experiments/<id>/pipeline.yaml` 로 정의, 스크립트는 `--exp <id>` 또는 `--all`
- 스크립트: `scripts/` (weekly_plan → daily_draft → course_assets → attach_photos → transit_table → refresh_conditions → fill_editor → weekly_report, export_excel 로 엑셀 정리·승인)
