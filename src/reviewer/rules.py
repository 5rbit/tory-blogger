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
    photos = re.findall(r"\[사진:|^!\[", markdown, flags=re.M)
    exp = re.findall(r"직접|제 경우|써보니|해보니", markdown)
    links = re.findall(r"https?://", markdown)
    tags = re.findall(r"(?<![\w#])#(?!#)[\w가-힣]+", markdown)
    return [
        RuleResult("글자수", len(body) >= r["min_chars"], f"{len(body)}자"),
        RuleResult("소제목", len(headings) >= r["min_headings"], f"{len(headings)}개"),
        RuleResult("사진 슬롯", len(photos) >= r["min_photo_slots"], f"{len(photos)}개"),
        RuleResult("경험 문장", len(exp) >= r["min_experience_sentences"], f"{len(exp)}개"),
        RuleResult("외부 링크", len(links) <= r["max_external_links"], f"{len(links)}개"),
        RuleResult("해시태그", r["hashtags"][0] <= len(tags) <= r["hashtags"][1], f"{len(tags)}개"),
        RuleResult("제목 길이", len(title) <= r["max_title_len"], f"{len(title)}자"),
        RuleResult("한줄요약(메이트)", "**한줄요약**" in markdown, "서두 요약 유무"),
        RuleResult("이모지 소제목", sum(1 for h in re.findall(r"^## (.)", markdown, flags=re.M) if not h.isalnum() and not h.isspace()) >= 3, "이모지로 시작하는 소제목 3개 이상"),
        RuleResult("표(실측)", bool(re.search(r"^\|.*\|\s*$", markdown, flags=re.M)), "Markdown 표 유무"),
        RuleResult("상품 슬롯(쇼핑커넥트)", len(re.findall(r"\[상품:", markdown)) <= 1, f"{len(re.findall(r'[[]상품:', markdown))}개"),
    ]
