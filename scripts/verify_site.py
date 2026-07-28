#!/usr/bin/env python3
"""Verify crawlability, static AdSense markup and recipe structured data."""

from __future__ import annotations

import json
import re
import sys
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
        if 'id="primary-nav"' not in value:
            fail(f"{post['slug']} has no crawlable primary navigation")
        if 'class="breadcrumbs"' not in value or 'class="related-recipes"' not in value:
            fail(f"{post['slug']} has no breadcrumbs or related recipes")
        if post["slug"] in TARGET_RECIPES and 'data-ad-placement="recipe-article"' not in value:
            fail(f"{post['slug']} has no static article ad unit")

    sitemap = ElementTree.parse(ROOT / "sitemap.xml")
    locations = [node.text or "" for node in sitemap.findall(".//{*}loc")]
    if len(locations) != 65:
        fail(f"sitemap should contain 65 canonical URLs, found {len(locations)}")
    if any("?p=" in location or "/feed/" in location or "sitemap_index" in location for location in locations):
        fail("sitemap contains a legacy or noncanonical URL")
    if "https://kfood.bumkok.com/korean-cooking-for-beginners/" not in locations:
        fail("sitemap is missing the beginner cooking guide")

    guide = (ROOT / "korean-cooking-for-beginners/index.html").read_text(encoding="utf-8")
    if '"@type":"Article"' not in guide:
        fail("beginner cooking guide is missing Article structured data")
    for target in ("dolsot-bibimbap", "yukgaejang", "godeungeo-gui"):
        if f'href="/{target}/"' not in guide:
            fail(f"beginner cooking guide is missing its {target} link")

    enhancements = {
        "dolsot-bibimbap": "Dolsot Bibimbap Troubleshooting",
        "yukgaejang": "Yukgaejang Troubleshooting",
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

    print(
        f"Verified {len(html_files)} HTML files, {len(POSTS)} recipe schemas, "
        f"{len(locations)} sitemap URLs and static AdSense markup."
    )


if __name__ == "__main__":
    main()
