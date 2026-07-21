#!/usr/bin/env python3
"""Build crawlable recipe pages at the original WordPress URLs."""

from __future__ import annotations

import html
import json
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "assets/data/posts-full.json"
SITE = "https://kfood.bumkok.com"
BUILD_DATE = date.today().isoformat()

# Historical duplicate URLs remain available, while their search signals are
# consolidated to the newer canonical copy.
CANONICAL_ALIASES = {
    "naengmyeon-kr": "naengmyeon-2",
    "galbijjim-kr": "galbijjim-kr-2",
}

# Pair translations only where the relationship was confirmed in the archive.
KO_TO_EN = {
    "%ea%b0%90%ec%9e%90%ed%83%95-gamjatang": "gamjatang",
    "miyeokguk-kr": "miyeokguk",
    "galbitang-2": "galbitang",
    "seolleongtang-2": "seolleongtang",
    "bibim-naengmyeon-2": "bibim-naengmyeon",
    "kongguksu-2": "kongguksu",
    "kimchi-fried-rice-2": "kimchi-fried-rice",
    "kalguksu-kr": "kalguksu",
    "yukgaejang-kr": "yukgaejang",
    "sundubu-jjigae-kr": "sundubu-jjigae",
    "budae-jjigae-kr": "budae-jjigae",
    "galbijjim-kr-2": "galbijjim",
    "galbijjim-kr": "galbijjim",
    "naengmyeon-2": "naengmyeon",
    "naengmyeon-kr": "naengmyeon",
    "pajeon-kr": "pajeon",
    "samgyetang-kr": "samgyetang",
    "doenjang-jjigae-kr": "doenjang-jjigae",
    "tteokbokki-kr": "tteokbokki",
    "kimchi-jjigae-2": "kimchi-jjigae",
    "dolsot-bibimbap-kr": "dolsot-bibimbap",
    "japchae-kr": "japchae",
    "bibimbap-2": "bibimbap",
    "bulgogi-2": "bulgogi",
    "gimbap": "gimbab",
}
EN_TO_KO = {}
for ko_slug, en_slug in KO_TO_EN.items():
    if ko_slug not in CANONICAL_ALIASES:
        EN_TO_KO[en_slug] = ko_slug


class ContentSanitizer(HTMLParser):
    """Remove migrated scripts, ad blocks, styles, forms and related cards."""

    blocked_tags = {"script", "style", "form"}
    blocked_classes = {"adsbygoogle", "wp-block-kadence-posts", "kb-posts"}
    void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.output: list[str] = []
        self.blocked_depth = 0

    def should_block(self, tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag in self.blocked_tags:
            return True
        classes = next((value or "" for key, value in attrs if key == "class"), "").split()
        return (tag == "ins" and "adsbygoogle" in classes) or bool(self.blocked_classes.intersection(classes))

    def handle_starttag(self, tag, attrs):
        if self.blocked_depth:
            self.blocked_depth += 1
            return
        if self.should_block(tag, attrs):
            self.blocked_depth = 1
            return
        rendered = []
        for key, value in attrs:
            if key.startswith("on"):
                continue
            rendered.append(key if value is None else f'{key}="{html.escape(value, quote=True)}"')
        suffix = (" " + " ".join(rendered)) if rendered else ""
        self.output.append(f"<{tag}{suffix}>")

    def handle_startendtag(self, tag, attrs):
        if self.blocked_depth or self.should_block(tag, attrs):
            return
        rendered = []
        for key, value in attrs:
            if key.startswith("on"):
                continue
            rendered.append(key if value is None else f'{key}="{html.escape(value, quote=True)}"')
        suffix = (" " + " ".join(rendered)) if rendered else ""
        self.output.append(f"<{tag}{suffix}>")

    def handle_endtag(self, tag):
        if self.blocked_depth:
            self.blocked_depth -= 1
            return
        if tag not in self.void_tags:
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.blocked_depth:
            self.output.append(data)

    def handle_entityref(self, name):
        if not self.blocked_depth:
            self.output.append(f"&{name};")

    def handle_charref(self, name):
        if not self.blocked_depth:
            self.output.append(f"&#{name};")

    def handle_comment(self, data):
        if not self.blocked_depth:
            self.output.append(f"<!--{data}-->")


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_content(value: str) -> str:
    parser = ContentSanitizer()
    parser.feed(value or "")
    parser.close()
    return "".join(parser.output).strip()


def seo_title(post: dict) -> str:
    full = clean_text(post["title"]).strip("\"“”")
    dish = full.split(":", 1)[0].strip("\"“”")
    if post["language"].startswith("ko"):
        return f"{dish} 레시피 | KFOOD Journal"
    if ":" not in full:
        dish = unquote(post["slug"]).replace("-", " ").title()
    return f"{dish} Korean Recipe | KFOOD Journal"


def canonical_url(post: dict, posts_by_slug: dict[str, dict]) -> str:
    alias_target = CANONICAL_ALIASES.get(post["slug"])
    return posts_by_slug[alias_target]["url"] if alias_target else post["url"]


def alternate_links(post: dict, posts_by_slug: dict[str, dict]) -> tuple[str, str]:
    slug = post["slug"]
    links = []
    alternate_url = ""
    if post["language"].startswith("ko"):
        en_slug = KO_TO_EN.get(slug)
        if en_slug and en_slug in posts_by_slug:
            alternate_url = posts_by_slug[en_slug]["url"]
            links.append(f'<link rel="alternate" hreflang="en" href="{html.escape(alternate_url)}">')
        links.append(f'<link rel="alternate" hreflang="ko" href="{html.escape(canonical_url(post, posts_by_slug))}">')
    else:
        ko_slug = EN_TO_KO.get(slug)
        links.append(f'<link rel="alternate" hreflang="en" href="{html.escape(canonical_url(post, posts_by_slug))}">')
        if ko_slug and ko_slug in posts_by_slug:
            alternate_url = posts_by_slug[ko_slug]["url"]
            links.append(f'<link rel="alternate" hreflang="ko" href="{html.escape(alternate_url)}">')
    return "".join(links), alternate_url


def recipe_schema(post: dict, canonical: str) -> str:
    image = post.get("image", "")
    if image.startswith("/"):
        image = SITE + image
    data = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "@id": canonical + "#recipe",
        "mainEntityOfPage": canonical,
        "name": clean_text(post["title"]),
        "description": clean_text(post.get("excerpt", ""))[:300],
        "image": [image] if image else [],
        "author": {"@type": "Organization", "name": "KFOOD Journal", "url": SITE + "/about/"},
        "datePublished": post.get("date"),
        "recipeCuisine": "Korean",
        "inLanguage": "ko" if post["language"].startswith("ko") else "en",
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def render(post: dict, posts_by_slug: dict[str, dict]) -> str:
    lang = "ko" if post["language"].startswith("ko") else "en"
    title = clean_text(post["title"])
    description = clean_text(post.get("excerpt", ""))[:160]
    canonical = canonical_url(post, posts_by_slug)
    alternates, alternate_url = alternate_links(post, posts_by_slug)
    image = post.get("image", "")
    absolute_image = SITE + image if image.startswith("/") else image
    back = "모든 레시피로 돌아가기" if lang == "ko" else "Back to all recipes"
    category = "한식 레시피" if lang == "ko" else "KOREAN RECIPE"
    recipe_archive = "/ko/recipes/" if lang == "ko" else "/recipes/"
    robots = '<meta name="robots" content="index,follow,max-image-preview:large">'
    body_alternate = f' data-alternate-url="{html.escape(urlparse(alternate_url).path, quote=True)}"' if alternate_url else ""
    lead = f'<img class="article-lead-image" src="{html.escape(image, quote=True)}" alt="{html.escape(title, quote=True)}" decoding="async" fetchpriority="high">' if image else ""
    return f'''<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(seo_title(post))}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  {robots}
  <link rel="canonical" href="{html.escape(canonical, quote=True)}">
  {alternates}
  <meta property="og:type" content="article">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:url" content="{html.escape(canonical, quote=True)}">
  <meta property="og:image" content="{html.escape(absolute_image, quote=True)}">
  <meta name="twitter:card" content="summary_large_image">
  <script type="application/ld+json">{recipe_schema(post, canonical)}</script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/webfontworld/scoredream/SCoreDream.css">
  <link rel="stylesheet" href="/styles.css">
  <link rel="stylesheet" href="/assets/pages.css">
</head>
<body class="page-shell"{body_alternate}>
  <div data-site-header></div>
  <main data-recipe-detail><article class="article-shell">
    <a class="article-back" href="{recipe_archive}">← {back}</a>
    <header class="article-header"><div><p class="article-kicker">{category}</p><h1 class="article-title">{html.escape(title)}</h1><p class="article-meta">{html.escape(post.get("date", ""))} · KFOOD JOURNAL</p></div>{lead}</header>
    <div class="article-body">{clean_content(post.get("content", ""))}</div>
  </article></main>
  <div data-site-footer></div>
  <script src="/assets/shared.js"></script>
  <script src="/assets/ads.js"></script>
</body>
</html>
'''


def render_archive(posts: list[dict], lang: str, canonical: str) -> str:
    ko = lang == "ko"
    selected = [post for post in posts if post["language"] == lang and post["slug"] not in CANONICAL_ALIASES]
    title = "한식 레시피 | KFOOD Journal" if ko else "Korean Recipes | KFOOD Journal"
    description = "집에서 만들 수 있는 한식 레시피를 음식 이름, 재료와 함께 찾아보세요." if ko else "Browse approachable Korean recipes with ingredients, context, and step-by-step cooking guidance."
    kicker = "한식 레시피 아카이브" if ko else "THE RECIPE ARCHIVE"
    heading = "오늘은<br><i>한식을 요리해요.</i>" if ko else "Cook <i>Korean.</i>"
    summary = "익숙한 집밥부터 새롭게 발견하는 메뉴까지, 음식의 이름과 배경을 지키며 친절하게 안내합니다." if ko else "Start with familiar comfort food or discover something new. Every recipe preserves its Korean name, context, and character."
    placeholder = "음식 이름이나 재료로 검색하세요…" if ko else "Search by dish or ingredient…"
    search_label = "레시피 검색" if ko else "Search recipes"
    rows = []
    items = []
    for index, post in enumerate(selected, 1):
        post_title = clean_text(post["title"])
        excerpt = clean_text(post.get("excerpt", ""))[:150]
        path = urlparse(post["url"]).path
        rows.append(f'<a class="recipe-row" href="{html.escape(path, quote=True)}"><span class="number">{index:02d}</span><div><h2>{html.escape(post_title)}</h2><p>{html.escape(excerpt)}</p></div><time>{html.escape(post.get("date", ""))}</time><b>↗</b></a>')
        items.append({"@type": "ListItem", "position": index, "url": post["url"], "name": post_title})
    schema = json.dumps({"@context": "https://schema.org", "@type": "ItemList", "itemListElement": items}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'''<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <link rel="canonical" href="{html.escape(canonical, quote=True)}">
  <link rel="alternate" hreflang="en" href="{SITE}/recipes/">
  <link rel="alternate" hreflang="ko" href="{SITE}/ko/recipes/">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:url" content="{html.escape(canonical, quote=True)}">
  <script type="application/ld+json">{schema}</script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/webfontworld/scoredream/SCoreDream.css">
  <link rel="stylesheet" href="/styles.css">
  <link rel="stylesheet" href="/assets/pages.css">
</head>
<body class="page-shell" data-alternate-url="{'/recipes/' if ko else '/ko/recipes/'}">
  <div data-site-header></div>
  <main>
    <section class="page-hero"><div><p class="eyebrow">{kicker}</p><h1>{heading}</h1></div><div class="page-hero-copy"><strong><span data-recipe-count>{len(selected)}</span> {'개의 레시피 · 집에서 쉽게' if ko else 'RECIPES · TESTED FOR HOME COOKS'}</strong>{summary}</div></section>
    <section class="content-section"><div class="filter-bar"><label class="sr-only" for="recipe-search">{search_label}</label><input id="recipe-search" data-recipe-search placeholder="{placeholder}"></div><div class="recipe-list" data-recipe-list>{''.join(rows)}</div></section>
  </main>
  <div data-site-footer></div>
  <script src="/assets/shared.js"></script>
  <script src="/assets/ads.js"></script>
  <script src="/assets/recipes.js?v=20260721-static"></script>
</body>
</html>
'''


def write_sitemap(posts: list[dict], posts_by_slug: dict[str, dict]) -> None:
    static_pages = ["/", "/recipes/", "/stories/", "/food-guide/", "/about/", "/contact/", "/privacy/", "/ko/", "/ko/recipes/", "/ko/stories/", "/ko/food-guide/", "/ko/about/", "/ko/contact/", "/ko/privacy/"]
    urls = [(SITE + path, BUILD_DATE) for path in static_pages]
    for post in posts:
        if post["slug"] in CANONICAL_ALIASES:
            continue
        urls.append((canonical_url(post, posts_by_slug), post.get("date") or BUILD_DATE))
    body = "\n".join(f"  <url><loc>{html.escape(url)}</loc><lastmod>{lastmod}</lastmod></url>" for url, lastmod in urls)
    (ROOT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n', encoding="utf-8")


def main() -> None:
    posts = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    posts_by_slug = {post["slug"]: post for post in posts}
    for post in posts:
        directory = ROOT / unquote(post["slug"])
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "index.html").write_text(render(post, posts_by_slug), encoding="utf-8")
    english_archive = render_archive(posts, "en", SITE + "/recipes/")
    korean_archive = render_archive(posts, "ko", SITE + "/ko/recipes/")
    (ROOT / "recipes/index.html").write_text(english_archive, encoding="utf-8")
    (ROOT / "ko/recipes/index.html").write_text(korean_archive, encoding="utf-8")
    (ROOT / "korean-recipes-en").mkdir(exist_ok=True)
    (ROOT / "korean-recipes-en/index.html").write_text(render_archive(posts, "en", SITE + "/recipes/"), encoding="utf-8")
    (ROOT / "korean-recipes-kr").mkdir(exist_ok=True)
    (ROOT / "korean-recipes-kr/index.html").write_text(render_archive(posts, "ko", SITE + "/ko/recipes/"), encoding="utf-8")
    write_sitemap(posts, posts_by_slug)
    (ROOT / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: https://kfood.bumkok.com/sitemap.xml\n", encoding="utf-8")
    (ROOT / "ads.txt").write_text("google.com, pub-5699330365644775, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    print(f"Generated {len(posts)} historical recipe routes and sitemap.xml")


if __name__ == "__main__":
    main()
