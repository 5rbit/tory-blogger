"""기존 발행 글과의 유사도 (문장 n-gram 자카드)."""
from __future__ import annotations
import re
from src.common import data_dir

def _ngrams(text: str, n: int = 3) -> set[str]:
    t = re.sub(r"\s+", "", text)
    return {t[i:i+n] for i in range(max(len(t) - n + 1, 0))}

def max_similarity(markdown: str) -> float:
    mine = _ngrams(markdown)
    best = 0.0
    for p in (data_dir() / "drafts").glob("*.md"):
        other = _ngrams(p.read_text(encoding="utf-8"))
        if mine and other:
            best = max(best, len(mine & other) / len(mine | other))
    return best
