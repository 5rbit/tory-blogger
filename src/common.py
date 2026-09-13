"""공통 유틸: 설정 로드, 로깅, 데이터 경로."""
from __future__ import annotations
import logging, os
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = ROOT / "config"
TEMPLATES = ROOT / "src" / "templates"

load_dotenv(ROOT / ".env")

def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    return logging.getLogger(name)

def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

def pipeline_config() -> dict:
    return load_yaml(CONFIG / "pipeline.yaml")

def env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)

@dataclass
class KeywordCandidate:
    keyword: str
    volume: int = 0            # 월 검색량 (PC+모바일)
    competition: float = 0.0   # 0~1
    personal_ratio: float = 0.0  # 상위 10 중 개인 블로그 비율
    source: str = "seed"
    post_type: str = "info"    # info | review | issue | hub
    angle: str = ""
    status: str = "pending"    # pending | approved | rejected | drafted | published
    extra: dict = field(default_factory=dict)

    def money_score(self, competition_bonus: float = 1.0, intent_bonus: float = 0.5, intent_words: list[str] | None = None) -> float:
        """돈 되는 키워드 점수: 검색량 × 개인 블로그 비율 × (1 + 경쟁도 가점) × (1 + 구매 의도 가점).
        경쟁도가 높다 = 광고주가 많다 = 단가가 높다."""
        intent = any(w in self.keyword for w in (intent_words or []))
        return (self.volume * max(self.personal_ratio, 0.05)
                * (1 + competition_bonus * self.competition)
                * (1 + (intent_bonus if intent else 0)))

    @property
    def score(self) -> float:
        return self.money_score()
