"""01 문서의 품질 원칙을 자동 검사한다."""
from __future__ import annotations
import re
from dataclasses import dataclass
from src.common import pipeline_config

@dataclass
class RuleResult:
    name: str
    passed: bool
    detail: str

def check(markdown: str, title: str) -> list[RuleResult]:
    r = pipeline_config()["review"]
    body = re.sub(r"\s", "", re.sub(r"#\S+", "", markdown))
    headings = re.findall(r"^##\s", markdown, flags=re.M)
    photos = re.findall(r"\[사진:", markdown)
    exp = re.findall(r"직접|제 경우|써보니|해보니", markdown)
    links = re.findall(r"https?://", markdown)
    tags = re.findall(r"(?<!\w)#\S+", markdown)
    return [
        RuleResult("글자수", len(body) >= r["min_chars"], f"{len(body)}자"),
        RuleResult("소제목", len(headings) >= r["min_headings"], f"{len(headings)}개"),
        RuleResult("사진 슬롯", len(photos) >= r["min_photo_slots"], f"{len(photos)}개"),
        RuleResult("경험 문장", len(exp) >= r["min_experience_sentences"], f"{len(exp)}개"),
        RuleResult("외부 링크", len(links) <= r["max_external_links"], f"{len(links)}개"),
        RuleResult("해시태그", r["hashtags"][0] <= len(tags) <= r["hashtags"][1], f"{len(tags)}개"),
        RuleResult("제목 길이", len(title) <= r["max_title_len"], f"{len(title)}자"),
    ]
