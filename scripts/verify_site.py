#!/usr/bin/env python3
"""Verify crawlability, static AdSense markup and recipe structured data."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
POSTS = json.loads((ROOT / "assets/data/posts-full.json").read_text(encoding="utf-8"))
TARGET_RECIPES = {
    "kimchi-jjigae",
    "naengmyeon",
    "samgyetang",
    "bulgogi",
    "doenjang-jjigae",
    "bibim-naengmyeon",
}
LOADER = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
CURRENT_YEAR = date.today().year
HYPE_PHRASES = (
    "perfect guide",
    "ultimate guide",
    "best ever",
    "완벽 가이드",
    "무조건 추천",
    "최강",
    "끝판왕",
    "인생템",
    "역대급",
)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def recipe_schema(value: str) -> dict:
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', value, re.S):
        data = json.loads(raw)
        if data.get("@type") == "Recipe":
            return data
    fail("Recipe JSON-LD not found")
    return {}


def main() -> None:
    html_files = list(ROOT.rglob("*.html"))
    if not html_files:
        fail("no HTML files found")
    for path in html_files:
        value = path.read_text(encoding="utf-8")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", value, re.I | re.S)
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else ""
        stale_years = [year for year in re.findall(r"20\d{2}", title) if int(year) < CURRENT_YEAR]
        if stale_years:
            fail(f"{path.relative_to(ROOT)} title contains stale year(s): {', '.join(stale_years)}")
        for phrase in HYPE_PHRASES:
            if phrase in title.lower():
                fail(f"{path.relative_to(ROOT)} title contains hype phrase: {phrase}")

        affiliate_anchors = re.findall(
            r'<a\b(?=[^>]*href=["\'][^"\']*(?:link\.coupang\.com|coupang\.com)[^"\']*["\'])[^>]*>',
            value,
            re.I,
        )
        for anchor in affiliate_anchors:
            rel_match = re.search(r'\brel=["\']([^"\']*)["\']', anchor, re.I)
            rel_tokens = set(rel_match.group(1).lower().split()) if rel_match else set()
            if not {"nofollow", "sponsored", "noopener"}.issubset(rel_tokens):
                fail(f"{path.relative_to(ROOT)} has an unlabelled affiliate link")
        if affiliate_anchors and "쿠팡 파트너스 활동의 일환" not in value:
            fail(f"{path.relative_to(ROOT)} is missing its affiliate disclosure")

        if value.count(LOADER) != 1:
            fail(f"{path.relative_to(ROOT)} must have exactly one static AdSense loader")
        if value.index(LOADER) > value.index("</head>"):
            fail(f"{path.relative_to(ROOT)} AdSense loader is outside <head>")

    for post in POSTS:
        path = ROOT / unquote(post["slug"]) / "index.html"
        value = path.read_text(encoding="utf-8")
        data = recipe_schema(value)
        if not data.get("recipeIngredient") or not data.get("recipeInstructions"):
            fail(f"{post['slug']} is missing recipe ingredients or instructions")
        for index, step in enumerate(data["recipeInstructions"], 1):
            if step.get("@type") != "HowToStep":
                fail(f"{post['slug']} instruction {index} is not a HowToStep")
            for field in ("name", "text", "url", "image"):
                if not step.get(field):
                    fail(f"{post['slug']} instruction {index} is missing {field}")
            if step["url"] != f"{data['mainEntityOfPage']}#recipe-step-{index}":
                fail(f"{post['slug']} instruction {index} has an unexpected URL")
        if 'id="primary-nav"' not in value:
            fail(f"{post['slug']} has no crawlable primary navigation")
        if 'class="breadcrumbs"' not in value or 'class="related-recipes"' not in value:
            fail(f"{post['slug']} has no breadcrumbs or related recipes")
        if post["slug"] in TARGET_RECIPES and 'data-ad-placement="recipe-article"' not in value:
            fail(f"{post['slug']} has no static article ad unit")

    sitemap = ElementTree.parse(ROOT / "sitemap.xml")
    locations = [node.text or "" for node in sitemap.findall(".//{*}loc")]
    if len(locations) != 66:
        fail(f"sitemap should contain 66 canonical URLs, found {len(locations)}")
    if any("?p=" in location or "/feed/" in location or "sitemap_index" in location for location in locations):
        fail("sitemap contains a legacy or noncanonical URL")
    if "https://kfood.bumkok.com/korean-cooking-for-beginners/" not in locations:
        fail("sitemap is missing the beginner cooking guide")
    if "https://kfood.bumkok.com/ko/korean-cooking-for-beginners/" not in locations:
        fail("sitemap is missing the Korean beginner cooking guide")

    audit_manifest = json.loads((ROOT / "audit-manifest.json").read_text(encoding="utf-8"))
    audit_targets = audit_manifest.get("targets", [])
    if len(audit_targets) < 7:
        fail("audit manifest is missing HTTP-only monitoring targets")
    if any(target.get("status") != 200 for target in audit_targets):
        fail("audit manifest contains a non-200 expected status")
    audit_urls = {target.get("url") for target in audit_targets}
    for required in (
        "https://kfood.bumkok.com/",
        "https://kfood.bumkok.com/robots.txt",
        "https://kfood.bumkok.com/ads.txt",
        "https://kfood.bumkok.com/sitemap.xml",
    ):
        if required not in audit_urls:
            fail(f"audit manifest is missing {required}")

    analytics = (ROOT / "assets/analytics.js").read_text(encoding="utf-8")
    for event_name in ("engaged_reader", "language_switch", "outbound_click"):
        if event_name not in analytics:
            fail(f"analytics is missing the {event_name} event")

    guide = (ROOT / "korean-cooking-for-beginners/index.html").read_text(encoding="utf-8")
    if '"@type":"Article"' not in guide:
        fail("beginner cooking guide is missing Article structured data")
    if 'og:image' not in guide or 'korean-cooking-beginners-hero.webp' not in guide:
        fail("beginner cooking guide is missing its hero image metadata")
    if 'href="https://kfood.bumkok.com/ko/korean-cooking-for-beginners/"' not in guide:
        fail("English beginner guide is missing its Korean hreflang")
    for target in ("dolsot-bibimbap", "yukgaejang", "godeungeo-gui"):
        if f'href="/{target}/"' not in guide:
            fail(f"beginner cooking guide is missing its {target} link")

    korean_guide = (ROOT / "ko/korean-cooking-for-beginners/index.html").read_text(encoding="utf-8")
    if '"@type":"Article"' not in korean_guide or '"inLanguage":"ko"' not in korean_guide:
        fail("Korean beginner cooking guide is missing Korean Article structured data")
    if 'og:image' not in korean_guide or 'korean-cooking-beginners-hero.webp' not in korean_guide:
        fail("Korean beginner cooking guide is missing its hero image metadata")
    if 'data-alternate-url="/korean-cooking-for-beginners/"' not in korean_guide:
        fail("Korean beginner guide is missing its English language switch")
    for target in ("dolsot-bibimbap-kr", "yukgaejang-kr", "godeungeo-gui"):
        if f'href="/{target}/"' not in korean_guide:
            fail(f"Korean beginner cooking guide is missing its {target} link")

    enhancements = {
        "dolsot-bibimbap": "Dolsot Bibimbap Troubleshooting",
        "yukgaejang": "Yukgaejang Troubleshooting",
        "galbitang": "Galbitang Troubleshooting",
        "godeungeo-gui": "Crispy-Skin Troubleshooting",
    }
    for slug, heading in enhancements.items():
        value = (ROOT / slug / "index.html").read_text(encoding="utf-8")
        if heading not in value or 'href="/korean-cooking-for-beginners/"' not in value:
            fail(f"{slug} is missing its editorial enhancement or beginner-guide link")

    for relative in (
        "index.html",
        "ko/index.html",
        "recipes/index.html",
        "ko/recipes/index.html",
        "stories/index.html",
        "ko/stories/index.html",
        "food-guide/index.html",
        "ko/food-guide/index.html",
    ):
        value = (ROOT / relative).read_text(encoding="utf-8")
        if "data-ad-placement=" not in value:
            fail(f"{relative} has no static content ad unit")

    home = (ROOT / "index.html").read_text(encoding="utf-8")
    if "Korean Recipes &amp; Cooking Guides | KFOOD Journal" not in home:
        fail("homepage is missing its search-focused title")
    if home.count('href="/korean-cooking-for-beginners/"') < 2:
        fail("homepage needs prominent links to the beginner cooking guide")

    korean_home = (ROOT / "ko/index.html").read_text(encoding="utf-8")
    if korean_home.count('href="/ko/korean-cooking-for-beginners/"') < 2:
        fail("Korean homepage needs prominent links to the Korean beginner guide")

    expected_titles = {
        "dolsot-bibimbap": "Dolsot Bibimbap Recipe: Crispy Rice | KFOOD Journal",
        "yukgaejang": "Yukgaejang Recipe: Spicy Korean Beef Soup | KFOOD Journal",
        "galbitang": "Galbitang Recipe: Korean Short Rib Soup | KFOOD Journal",
    }
    for slug, title in expected_titles.items():
        value = (ROOT / slug / "index.html").read_text(encoding="utf-8")
        if f"<title>{title}</title>" not in value:
            fail(f"{slug} has an unexpected search title")

    print(
        f"Verified {len(html_files)} HTML files, {len(POSTS)} recipe schemas, "
        f"{len(locations)} sitemap URLs, editorial rules, HTTP-only audit targets and static AdSense markup."
    )


if __name__ == "__main__":
    main()
