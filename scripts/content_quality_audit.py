#!/usr/bin/env python3
"""Rank KFOOD recipe pages for evidence-backed editorial cleanup."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
POSTS = json.loads((ROOT / "assets/data/posts-full.json").read_text(encoding="utf-8"))
PRIORITY_IMPRESSIONS = {
    "yukgaejang": 124,
    "galbitang": 68,
    "dolsot-bibimbap": 66,
    "sundubu-jjigae": 66,
    "haemultang": 36,
    "godeungeo-gui": 27,
}
HYPE = re.compile(
    r"\b(?:perfect|ultimate|best ever|life[- ]changing|secret)\b|"
    r"완벽|무조건|최강|끝판왕|인생템|역대급|최고|비밀",
    re.I,
)
FIRST_PERSON_EXPERIENCE = re.compile(
    r"\b(?:I (?:first|tried|used|bought|remember|was|went|ordered)|my first)\b|"
    r"(?:제가|저는|처음\s+[^.!?]{0,30}(?:먹|가|써|사용|만들|주문)|직접\s*(?:먹|써|사용|구매|만들|확인))",
    re.I,
)


def visible_text(value: str) -> str:
    value = re.sub(r"<(?:script|style)\b.*?</(?:script|style)>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def extract(pattern: str, value: str) -> str:
    match = re.search(pattern, value, flags=re.I | re.S)
    return visible_text(match.group(1)) if match else ""


def inspect(post: dict) -> dict:
    path = ROOT / unquote(post["slug"]) / "index.html"
    value = path.read_text(encoding="utf-8")
    body = extract(r"<div class=\"article-body\">(.*?)</div>\s*(?:<nav|<section)", value)
    title = extract(r"<title[^>]*>(.*?)</title>", value)
    heading = extract(r"<h1[^>]*>(.*?)</h1>", value)
    description_match = re.search(r'<meta name="description" content="([^"]*)"', value, re.I)
    description = html.unescape(description_match.group(1)) if description_match else ""
    hype_hits = len(HYPE.findall(body))
    experience_hits = len(FIRST_PERSON_EXPERIENCE.findall(body))
    impressions = PRIORITY_IMPRESSIONS.get(post["slug"], 0)
    score = impressions * 10 + experience_hits * 30 + hype_hits * 5
    return {
        "slug": post["slug"],
        "language": post["language"],
        "title": title,
        "heading": heading,
        "description": description,
        "search_impressions_3m": impressions,
        "first_person_experience_hits": experience_hits,
        "hype_hits": hype_hits,
        "has_og_image": 'property="og:image"' in value,
        "has_recipe_schema": '"@type":"Recipe"' in value,
        "priority_score": score,
        "review_required": bool(experience_hits or hype_hits),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()

    pages = sorted((inspect(post) for post in POSTS), key=lambda item: item["priority_score"], reverse=True)
    summary = {
        "recipe_pages": len(pages),
        "review_required_pages": sum(item["review_required"] for item in pages),
        "first_person_experience_pages": sum(item["first_person_experience_hits"] > 0 for item in pages),
        "hype_pages": sum(item["hype_hits"] > 0 for item in pages),
        "missing_og_image_pages": sum(not item["has_og_image"] for item in pages),
        "priority_pages": pages[: args.limit],
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    print(
        "Content quality audit: "
        f"{summary['recipe_pages']} recipes, "
        f"{summary['review_required_pages']} need review, "
        f"{summary['first_person_experience_pages']} contain unsupported first-person signals, "
        f"{summary['hype_pages']} contain promotional wording."
    )
    print("Priority order (Search Console impressions are the 2026-08-03 baseline):")
    for item in summary["priority_pages"]:
        print(
            f"- {item['slug']}: score={item['priority_score']}, "
            f"impressions={item['search_impressions_3m']}, "
            f"first_person={item['first_person_experience_hits']}, hype={item['hype_hits']}"
        )


if __name__ == "__main__":
    main()
