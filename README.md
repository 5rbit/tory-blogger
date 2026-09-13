# tory-blogger — 네이버 블로그 수익 창출 전략 및 실행 자동화

네이버 블로그를 **수익형 미디어**로 키우기 위한 전략과, 사람 개입을 주 3시간 이내로 줄이는 반자동 파이프라인 계획입니다.

## 문서 구성

| 문서 | 내용 |
|------|------|
| [docs/01-수익화-전략.md](docs/01-수익화-전략.md) | 수익원 5가지, 주제 선정, C-Rank/D.I.A. 대응 원칙, 글 유형 비율, 금지 사항 |
| [docs/02-자동화-실행-계획.md](docs/02-자동화-실행-계획.md) | 반자동 파이프라인 아키텍처, 모듈별 설계, 휴먼 게이트 |
| [docs/03-로드맵-및-KPI.md](docs/03-로드맵-및-KPI.md) | 12주 로드맵, 측정 지표, 리스크 |

## 전제

- 플랫폼: 네이버 블로그 1개 (주제 집중)
- 발행 방식: 초안 생성·검수·에디터 채우기는 자동, **발행 버튼은 사람이 클릭**
- 글 생성: Claude API (`claude-sonnet-5` 기본, 품질 채점은 `claude-fable-5-1`)
- 키워드 발굴: 네이버 검색광고 API + 네이버 검색 API (공식)
- 사람 역할: 주 1회 키워드 승인, 매 글 사진 첨부·최종 검토·발행

## 빠른 시작

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # 네이버 API 키 입력
python scripts/weekly_plan.py --dry-run
python scripts/daily_draft.py --dry-run
```

## 파이프라인 한눈에 보기

```
research → planner → writer → reviewer → [사람 승인] → publisher(에디터 채움) → [사람 발행] → distributor → analytics
```
