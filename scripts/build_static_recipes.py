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
ADSENSE_PUBLISHER_ID = "ca-pub-5699330365644775"
ADSENSE_SLOT_ID = "1340029023"
ADSENSE_LOADER = (
    '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
    f'?client={ADSENSE_PUBLISHER_ID}" crossorigin="anonymous"></script>'
)

# Only publish timings stated by the recipes themselves. We deliberately leave
# rating, nutrition and video fields out until first-party values exist.
RECIPE_TIMES = {
    "naengmyeon": {"prepTime": "PT5H30M", "cookTime": "PT4H"},
    "samgyetang": {"prepTime": "PT6H", "cookTime": "PT1H30M"},
    "bulgogi": {"prepTime": "PT1H", "cookTime": "PT4M"},
    "doenjang-jjigae": {"cookTime": "PT23M"},
    "kimchi-jjigae": {"cookTime": "PT23M"},
}

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


class RecipeStructureParser(HTMLParser):
    """Extract ingredients and cooking steps already present in a recipe."""

    ingredient_heading = re.compile(
        r"ingredients?|(?:everything|what).{0,30}need|재료|준비물|필요한.{0,15}재료",
        re.I,
    )
    instruction_heading = re.compile(
        r"step.by.step|prepar(?:ation|ing)|cooking (?:process|method|methods)|"
        r"let.?s (?:create|cook|make)|make some magic|만들|끓이|조리|요리|과정|방법|단계|마법",
        re.I,
    )

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.capture = ""
        self.buffer: list[str] = []
        self.blocks: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"h2", "h3", "li", "p"}:
            self.capture = tag
            self.buffer = []

    def handle_data(self, data):
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag != self.capture:
            return
        text = re.sub(r"\s+", " ", " ".join(self.buffer)).strip()
        if text:
            self.blocks.append((tag, text))
        self.capture = ""
        self.buffer = []


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_content(value: str) -> str:
    parser = ContentSanitizer()
    parser.feed(value or "")
    parser.close()
    return "".join(parser.output).strip()


def unique_text(items: list[str], limit: int) -> list[str]:
    result = []
    seen = set()
    for item in items:
        normalized = clean_text(item)
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
        if len(result) == limit:
            break
    return result


def recipe_details(post: dict) -> tuple[list[str], list[str]]:
    parser = RecipeStructureParser()
    parser.feed(post.get("content", ""))
    parser.close()
    ingredient_start = next(
        (index for index, (tag, text) in enumerate(parser.blocks)
         if tag in {"h2", "h3"} and parser.ingredient_heading.search(text)),
        None,
    )
    instruction_start = next(
        (index for index, (tag, text) in enumerate(parser.blocks)
         if tag in {"h2", "h3"} and parser.instruction_heading.search(text)
         and (ingredient_start is None or index > ingredient_start)),
        None,
    )
    ingredients = []
    if ingredient_start is not None:
        end = instruction_start if instruction_start is not None else len(parser.blocks)
        ingredients = [text for tag, text in parser.blocks[ingredient_start + 1:end] if tag == "li"]
    instructions = []
    if instruction_start is not None:
        end = len(parser.blocks)
        for index in range(instruction_start + 1, len(parser.blocks)):
            tag, text = parser.blocks[index]
            if tag == "h2" and not parser.instruction_heading.search(text):
                end = index
                break
        instructions = [
            text for tag, text in parser.blocks[instruction_start + 1:end]
            if tag in {"li", "p"}
        ]
    return unique_text(ingredients, 80), unique_text(instructions, 80)


def recipe_category(post: dict) -> str:
    title = clean_text(post["title"]).casefold()
    if re.search(r"jjigae|탕|guk|soup|stew|국", title):
        return "Korean soup and stew"
    if re.search(r"naengmyeon|kalguksu|kongguksu|noodle|면|국수", title):
        return "Korean noodles"
    if re.search(r"bibimbap|fried rice|gimbap|kimbap|밥|김밥", title):
        return "Korean rice dish"
    if re.search(r"bulgogi|galbi|barbecue|bbq|구이|불고기", title):
        return "Korean main course"
    return "Korean recipe"


def recipe_keywords(post: dict) -> list[str]:
    title = clean_text(post["title"])
    dish = title.split(":", 1)[0].strip("\"“”")
    content = clean_text(post.get("content", ""))
    hashtags = re.findall(r"#([A-Za-z가-힣][\w가-힣-]+)", content)
    defaults = ["한식", "한식 레시피"] if post["language"].startswith("ko") else ["Korean food", "Korean recipe"]
    return unique_text([dish, *hashtags, *defaults], 12)


def ad_zone(placement: str, ko: bool = False) -> str:
    label = "광고" if ko else "ADVERTISEMENT"
    classes = "ad-zone ad-zone-in-list" if placement == "recipe-archive" else "ad-zone"
    return f'''<aside class="{classes}" data-ad-placement="{placement}" aria-label="{label}">
      <span class="ad-zone-label">{label}</span>
      <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_PUBLISHER_ID}" data-ad-slot="{ADSENSE_SLOT_ID}" data-ad-format="auto" data-full-width-responsive="true"></ins>
      <script>(window.adsbygoogle=window.adsbygoogle||[]).push({{}});</script>
    </aside>'''


def site_header(lang: str, alternate_url: str = "") -> str:
    ko = lang == "ko"
    prefix = "/ko" if ko else ""
    alternate = alternate_url or ("/" if ko else "/ko/")
    labels = {
        "recipes": "레시피" if ko else "Recipes",
        "stories": "이야기" if ko else "Stories",
        "guide": "한식 가이드" if ko else "Food Guide",
        "about": "소개" if ko else "About",
        "contact": "문의" if ko else "Contact",
        "find": "레시피 찾기" if ko else "Find a recipe",
        "menu": "메뉴" if ko else "Menu",
        "language": "EN" if ko else "한국어",
    }
    announcement = "매주 새로운 레시피를 만나보세요" if ko else "New recipes every week"
    return f'''<div class="announcement">Korean food, remembered and shared <span>·</span> {announcement}</div>
    <header class="site-header">
      <a class="wordmark" href="{prefix}/" aria-label="KFOOD Journal home">KFOOD <em>Journal</em></a>
      <button class="menu-button" aria-expanded="false" aria-controls="primary-nav">{labels["menu"]}</button>
      <nav id="primary-nav" class="primary-nav" aria-label="Primary navigation">
        <a href="{prefix}/recipes/">{labels["recipes"]}</a><a href="{prefix}/stories/">{labels["stories"]}</a><a href="{prefix}/food-guide/">{labels["guide"]}</a><a href="{prefix}/about/">{labels["about"]}</a><a href="{prefix}/contact/">{labels["contact"]}</a>
      </nav>
      <a class="language-link" href="{html.escape(alternate, quote=True)}" lang="{"en" if ko else "ko"}">{labels["language"]}</a>
      <a class="search-link" href="{prefix}/recipes/">{labels["find"]} <span>↗</span></a>
    </header>'''


def site_footer(lang: str) -> str:
    ko = lang == "ko"
    prefix = "/ko" if ko else ""
    about = "소개" if ko else "About"
    contact = "문의" if ko else "Contact"
    privacy = "개인정보처리방침" if ko else "Privacy"
    return f'''<footer class="site-footer route-footer"><a class="wordmark" href="{prefix}/">KFOOD <em>Journal</em></a><p>© 2026 KFOOD Journal. Korean flavors, globally shared.</p><div><a href="{prefix}/about/">{about}</a><a href="{prefix}/contact/">{contact}</a><a href="{prefix}/privacy/">{privacy}</a></div></footer>'''


def insert_article_ad(content: str, ko: bool) -> str:
    headings = list(re.finditer(r"<h2\b", content, re.I))
    if not headings:
        return content + ad_zone("recipe-article", ko)
    anchor = headings[max(1, len(headings) // 2)] if len(headings) > 1 else headings[0]
    return content[:anchor.start()] + ad_zone("recipe-article", ko) + content[anchor.start():]


def recipe_links(post: dict, posts: list[dict]) -> tuple[str, str]:
    lang = "ko" if post["language"].startswith("ko") else "en"
    selected = [item for item in posts if item["language"].startswith(lang) and item["slug"] not in CANONICAL_ALIASES]
    current = selected.index(post) if post in selected else 0
    previous = selected[current - 1] if current else selected[-1]
    following = selected[(current + 1) % len(selected)]
    candidates = [item for item in selected if item is not post]
    related = [candidates[(current + offset) % len(candidates)] for offset in range(min(3, len(candidates)))]
    previous_label = "이전 레시피" if lang == "ko" else "Previous recipe"
    next_label = "다음 레시피" if lang == "ko" else "Next recipe"
    related_label = "함께 볼 레시피" if lang == "ko" else "Related recipes"
    pager = f'''<nav class="article-pager" aria-label="Recipe pagination">
      <a rel="prev" href="{html.escape(urlparse(previous["url"]).path, quote=True)}"><small>← {previous_label}</small><strong>{html.escape(clean_text(previous["title"]))}</strong></a>
      <a rel="next" href="{html.escape(urlparse(following["url"]).path, quote=True)}"><small>{next_label} →</small><strong>{html.escape(clean_text(following["title"]))}</strong></a>
    </nav>'''
    cards = "".join(
        f'<a href="{html.escape(urlparse(item["url"]).path, quote=True)}"><span>{index:02d}</span><strong>{html.escape(clean_text(item["title"]))}</strong></a>'
        for index, item in enumerate(related, 1)
    )
    related_html = f'<section class="related-recipes"><p class="article-kicker">{related_label}</p><div>{cards}</div></section>'
    return pager, related_html


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
        "recipeCategory": recipe_category(post),
        "keywords": recipe_keywords(post),
        "inLanguage": "ko" if post["language"].startswith("ko") else "en",
    }
    ingredients, instructions = recipe_details(post)
    if ingredients:
        data["recipeIngredient"] = ingredients
    if instructions:
        data["recipeInstructions"] = [
            {"@type": "HowToStep", "position": index, "text": text}
            for index, text in enumerate(instructions, 1)
        ]
    data.update(RECIPE_TIMES.get(post["slug"], {}))
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
    cleaned_content = insert_article_ad(clean_content(post.get("content", "")), lang == "ko")
    pager, related = recipe_links(post, list(posts_by_slug.values()))
    home_label = "홈" if lang == "ko" else "Home"
    recipes_label = "레시피" if lang == "ko" else "Recipes"
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
  {ADSENSE_LOADER}
</head>
<body class="page-shell"{body_alternate}>
  <div data-site-header>{site_header(lang, urlparse(alternate_url).path if alternate_url else "")}</div>
  <main data-recipe-detail><article class="article-shell">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="{'/ko/' if lang == 'ko' else '/'}">{home_label}</a><span>›</span><a href="{recipe_archive}">{recipes_label}</a><span>›</span><span aria-current="page">{html.escape(title)}</span></nav>
    <a class="article-back" href="{recipe_archive}">← {back}</a>
    <header class="article-header"><div><p class="article-kicker">{category}</p><h1 class="article-title">{html.escape(title)}</h1><p class="article-meta">{html.escape(post.get("date", ""))} · KFOOD JOURNAL</p></div>{lead}</header>
    <div class="article-body">{cleaned_content}</div>
    {pager}
    {related}
  </article></main>
  <div data-site-footer>{site_footer(lang)}</div>
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
        if index == 8:
            rows.append(ad_zone("recipe-archive", ko))
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
  {ADSENSE_LOADER}
</head>
<body class="page-shell" data-alternate-url="{'/recipes/' if ko else '/ko/recipes/'}">
  <div data-site-header>{site_header(lang, "/recipes/" if ko else "/ko/recipes/")}</div>
  <main>
    <section class="page-hero"><div><p class="eyebrow">{kicker}</p><h1>{heading}</h1></div><div class="page-hero-copy"><strong><span data-recipe-count>{len(selected)}</span> {'개의 레시피 · 집에서 쉽게' if ko else 'RECIPES · TESTED FOR HOME COOKS'}</strong>{summary}</div></section>
    <section class="content-section"><div class="filter-bar"><label class="sr-only" for="recipe-search">{search_label}</label><input id="recipe-search" data-recipe-search placeholder="{placeholder}"></div><div class="recipe-list" data-recipe-list>{''.join(rows)}</div></section>
  </main>
  <div data-site-footer>{site_footer(lang)}</div>
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


def hydrate_static_pages() -> None:
    """Keep ads and crawlable navigation in the raw HTML, not JS-only."""

    content_ad_pages = {
        "index.html",
        "ko/index.html",
        "stories/index.html",
        "ko/stories/index.html",
        "food-guide/index.html",
        "ko/food-guide/index.html",
    }
    static_chrome_pages = {
        "about/index.html",
        "contact/index.html",
        "privacy/index.html",
        "recipe/index.html",
        "stories/index.html",
        "food-guide/index.html",
        "ko/about/index.html",
        "ko/contact/index.html",
        "ko/privacy/index.html",
        "ko/recipe/index.html",
        "ko/stories/index.html",
        "ko/food-guide/index.html",
    }
    for path in ROOT.rglob("*.html"):
        relative = path.relative_to(ROOT).as_posix()
        value = path.read_text(encoding="utf-8")
        lang = "ko" if relative.startswith("ko/") or 'lang="ko"' in value[:200] else "en"
        route = "/" + relative.removesuffix("index.html")
        if lang == "ko" and route.startswith("/ko/"):
            alternate = route.removeprefix("/ko") or "/"
        else:
            alternate = "/ko" + route
        if "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js" not in value:
            value = value.replace("</head>", f"  {ADSENSE_LOADER}\n</head>", 1)
        value = re.sub(
            r"<div data-site-header>\s*</div>",
            lambda _: f"<div data-site-header>{site_header(lang, alternate)}</div>",
            value,
            count=1,
        )
        value = re.sub(
            r"<div data-site-footer>\s*</div>",
            lambda _: f"<div data-site-footer>{site_footer(lang)}</div>",
            value,
            count=1,
        )
        if relative in static_chrome_pages:
            value = re.sub(
                r"<div data-site-header>.*?</header></div>",
                lambda _: f"<div data-site-header>{site_header(lang, alternate)}</div>",
                value,
                count=1,
                flags=re.S,
            )
            value = re.sub(
                r"<div data-site-footer>.*?</footer></div>",
                lambda _: f"<div data-site-footer>{site_footer(lang)}</div>",
                value,
                count=1,
                flags=re.S,
            )
        if relative in content_ad_pages and "data-ad-placement=" not in value:
            value = value.replace("</main>", f'{ad_zone("content", lang == "ko")}\n</main>', 1)
        path.write_text(value, encoding="utf-8")


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
    hydrate_static_pages()
    print(f"Generated {len(posts)} historical recipe routes and sitemap.xml")


if __name__ == "__main__":
    main()
