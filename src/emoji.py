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
DIFFICULTY = {1: "🥾 쉬움", 2: "🥾🥾 무난", 3: "🥾🥾🥾 보통", 4: "🥾🥾🥾🥾 힘듦", 5: "🥾🥾🥾🥾🥾 매우 힘듦"}
_LABEL_TO_LEVEL = {"쉬움": 1, "하": 1, "무난": 2, "보통": 3, "중": 3, "힘듦": 4, "어려움": 4, "상": 4, "매우어려움": 5, "매우힘듦": 5}

def difficulty_emoji(level_or_label: int | str | None) -> str:
    if level_or_label is None or level_or_label == "":
        return "🥾 -"
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
