"""블로그 전반에서 쓰는 이모지 규칙 (한 곳에서 관리)."""
from __future__ import annotations

E = {
    "summary": "📌", "course": "🥾", "season": "🍁", "photo": "📷", "map": "🗺️", "gear": "🎒", "food": "🍲",
    "transit": "🚌", "subway": "🚇", "bus": "🚌", "warning": "⚠️", "weather": "🌤️", "rain": "🌧️", "snow": "❄️",
    "sun": "☀️", "cloud": "☁️", "start": "🚩", "peak": "⛰️", "lunch": "🍱", "finish": "🏁", "parking": "🅿️",
    "toilet": "🚻", "time": "⏱️", "distance": "📏", "elevation": "📈", "closed": "⛔", "ok": "✅", "tip": "💡",
    "view": "🌄", "water": "💧", "nomad": "💻",
}

# 난이도: 등산화 개수 + 이름
# 등급 아이콘은 🥾(개수), '난이도' 라벨 아이콘은 💪 로 구분
DIFFICULTY_LABEL = "💪 난이도"
LEVEL_NAME = {1: "산책 수준", 2: "가볍게", 3: "땀 좀 나요", 4: "빡센 편", 5: "극한 도전"}
DIFFICULTY = {k: f"{'🥾' * k} {v}" for k, v in LEVEL_NAME.items()}
_LABEL_TO_LEVEL = {"쉬움": 1, "하": 1, "산책수준": 1, "무난": 2, "가볍게": 2, "보통": 3, "중": 3, "땀좀나요": 3,
                   "힘듦": 4, "어려움": 4, "상": 4, "빡센편": 4, "매우어려움": 5, "매우힘듦": 5, "극한도전": 5}

def difficulty_emoji(level_or_label: int | str | None) -> str:
    if level_or_label is None or level_or_label == "":
        return "🥾 미정"
    lvl = level_or_label if isinstance(level_or_label, int) else _LABEL_TO_LEVEL.get(str(level_or_label).replace(" ", ""), 3)
    return DIFFICULTY[max(1, min(5, lvl))]

def boots(level: int) -> str:
    return "🥾" * max(1, min(5, level))

def weather_emoji(sky: str) -> str:
    s = sky or ""
    if "눈" in s: return E["snow"]
    if "비" in s or "소나기" in s: return E["rain"]
    if "흐림" in s: return E["cloud"]
    if "구름" in s: return "⛅"
    if "맑" in s: return E["sun"]
    return E["weather"]

def foliage_emoji(status: str) -> str:
    if "절정" in status and "지남" not in status and "까지" not in status: return "🍁🍁🍁"
    if "지남" in status: return "🍂"
    if "진행" in status: return "🍁🍁"
    return "🍃"
