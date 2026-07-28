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

POST_OVERRIDES = {
    "dolsot-bibimbap": {
        "title": "Dolsot Bibimbap Recipe: Crispy Rice in a Korean Stone Bowl",
        "excerpt": (
            "Make dolsot bibimbap with seasoned vegetables, rice, egg, and gochujang, "
            "plus practical steps for a crisp nurungji crust and safe stone-bowl handling."
        ),
        "replacements": [
            (
                "<p class=\"wp-block-paragraph\">Some food historians believe it evolved from &#8220;Gujeolpan,&#8221; a royal court dish from the Joseon Dynasty. Either way, it beautifully reflects Korean food philosophy – harmoniously bringing together multiple ingredients in a single vessel.</p>",
                "<p class=\"wp-block-paragraph\">The exact origin of the modern stone-bowl presentation is not settled. What matters in the kitchen is the method: a well-heated bowl keeps the meal hot and creates the crisp rice layer called nurungji.</p>",
            ),
            (
                "<li>At restaurants, your bowl arrives pre-heated to around 350-400°F</li>",
                "<li>At restaurants, the bowl arrives extremely hot; exact temperatures vary by bowl and stove.</li>",
            ),
            (
                "<li><strong>Far-infrared emission</strong>: The stone actually emits rays that enhance the natural flavors of your food.</li>",
                "<li><strong>Steady residual heat</strong>: The heavy bowl continues cooking the rice after it leaves the burner.</li>",
            ),
        ],
        "append": """
<h2 class="wp-block-heading">Dolsot Bibimbap Troubleshooting</h2>
<ul class="wp-block-list">
<li><strong>No crisp rice layer:</strong> Preheat the bowl gradually, use warm rice, and leave the assembled rice undisturbed for 2 to 3 minutes before mixing.</li>
<li><strong>Rice burns before the toppings are warm:</strong> Lower the heat. A stone bowl stores heat, so medium or medium-low heat is usually enough once it is hot.</li>
<li><strong>The bottom turns soggy:</strong> Drain and squeeze blanched vegetables well before adding them.</li>
<li><strong>The egg stays too raw:</strong> Use a fully fried egg, or cover the bowl briefly so the residual heat cooks it further.</li>
</ul>

<h2 class="wp-block-heading">No Stone Bowl? Use Cast Iron</h2>
<p class="wp-block-paragraph">A small cast-iron skillet will not produce exactly the same table-side experience, but it can make a good crisp rice crust. Brush the hot skillet lightly with oil, press in warm rice, add the toppings, and cook over medium-low heat until the edges audibly sizzle. Protect the table with a heatproof trivet.</p>

<h2 class="wp-block-heading">Stone Bowl Safety</h2>
<p class="wp-block-paragraph">Check the manufacturer’s instructions before using a bowl on direct heat. Warm stone cookware gradually, keep it away from cold water while hot, and use dry oven mitts. The bowl remains hot long after serving. Use a fully cooked egg for diners who avoid raw or undercooked eggs.</p>

<p class="wp-block-paragraph">New to Korean cooking? Start with our <a href="/korean-cooking-for-beginners/">five-dish Korean cooking plan</a>, or compare this recipe with <a href="/bibimbap/">classic bibimbap</a> and <a href="/bulgogi/">bulgogi</a>.</p>
""",
    },
    "yukgaejang": {
        "title": "Yukgaejang Recipe: Spicy Korean Beef Soup",
        "excerpt": (
            "Cook yukgaejang, a spicy Korean beef soup with shredded brisket, green onion, "
            "bean sprouts, and gochugaru, with substitutions and troubleshooting tips."
        ),
        "replacements": [
            (
                "<p class=\"wp-block-paragraph\">Yukgaejang evolved as a variation of Seolleongtang (ox bone soup) during the Joseon Dynasty, originally called &#8220;Yukgye&#8221; or &#8220;Yukgi.&#8221; It began as a nourishing dish enjoyed by the royal family and nobility but gradually became beloved by the general population. Traditional Yukgaejang was characterized by its rich beef broth simmered for hours, enhanced with spicy red pepper powder for an invigorating kick. Historically, various beef parts including offal (tripe, lungs, intestines) were used, but modern versions primarily use brisket or shank. Today, it&#8217;s a popular hangover remedy and a go-to dish when Koreans need physical and spiritual fortification.</p>",
                "<p class=\"wp-block-paragraph\">Yukgaejang is a Korean spicy beef soup built from a clear beef broth, shredded meat, green onion, vegetables, garlic, and gochugaru. Recipes vary by household and region; brisket and shank are practical modern choices because they become tender enough to shred while flavoring the broth.</p>",
            ),
            (
                "<p class=\"wp-block-paragraph\">A bowl of Yukgaejang is much more than just a meal—it&#8217;s a warm embrace offering strength when you&#8217;re feeling weak, a spicy revival for tired bodies, and a source of energy rooted in centuries of Korean culinary wisdom. The moment the fiery broth touches your lips and travels down your throat, a comforting warmth spreads throughout your body, instilling confidence to overcome any challenge. Why not share this revitalizing experience with loved ones after a long, tiring day or during the depths of winter?</p>",
                "<p class=\"wp-block-paragraph\">Yukgaejang is especially satisfying when served hot with plain rice and a crisp side dish such as kkakdugi. Let leftovers cool promptly, refrigerate them in a covered container, and reheat only the portion you plan to eat.</p>",
            ),
        ],
        "append": """
<h2 class="wp-block-heading">Ingredient Substitutions That Keep the Soup Balanced</h2>
<ul class="wp-block-list">
<li><strong>No gosari:</strong> Use sliced shiitake or oyster mushrooms for a chewy, savory element. The result is not traditional, but it keeps the soup satisfying.</li>
<li><strong>No taro stems:</strong> Leave them out and add more green onion or mushrooms instead.</li>
<li><strong>No brisket:</strong> Beef shank or chuck works when simmered until it shreds easily.</li>
<li><strong>Less heat:</strong> Reduce the gochugaru, but keep the garlic, soy sauce, and green onion so the broth still has depth.</li>
</ul>

<h2 class="wp-block-heading">How to Keep Gochugaru from Turning Bitter</h2>
<p class="wp-block-paragraph">Gochugaru can scorch quickly in hot oil. Warm the oil over low heat, remove the pot from direct heat if necessary, and stir in the pepper flakes only until fragrant. Add broth before the flakes darken. If the soup tastes harsh, dilute it with unsalted broth and correct the seasoning at the end.</p>

<h2 class="wp-block-heading">Yukgaejang Troubleshooting</h2>
<ul class="wp-block-list">
<li><strong>Cloudy or greasy broth:</strong> Keep the beef at a gentle simmer and skim foam and excess fat as it cooks.</li>
<li><strong>Tough beef:</strong> Continue simmering before shredding; the meat should separate with light pressure.</li>
<li><strong>Flat flavor:</strong> Adjust soup soy sauce and salt separately. Soy sauce adds aroma and color, while salt raises seasoning without darkening the broth.</li>
<li><strong>Soft bean sprouts:</strong> Add them near the end and avoid prolonged reheating.</li>
</ul>

<p class="wp-block-paragraph">Build confidence with the <a href="/korean-cooking-for-beginners/">Korean cooking starter plan</a>, then try <a href="/seolleongtang/">seolleongtang</a> for a mild beef soup or <a href="/sundubu-jjigae/">sundubu jjigae</a> for another spicy broth.</p>
""",
    },
    "godeungeo-gui": {
        "title": "Godeungeo Gui Recipe: Korean Grilled Mackerel with Crispy Skin",
        "excerpt": (
            "Make Korean grilled mackerel with crisp skin and juicy flesh using a grill, "
            "skillet, oven, or air fryer, with practical tips for salting, odor, and bones."
        ),
        "replacements": [
            (
                "<p class=\"wp-block-paragraph\">Confession time! I used to be one of those people who thought fish was either &#8220;expensive sushi&#8221; or &#8220;boring dinner protein.&#8221; Then I stumbled into a Korean BBQ place that had this whole section dedicated to grilled fish, and out of curiosity (and peer pressure from Korean friends), I ordered godeungeo-gui.</p>",
                "<p class=\"wp-block-paragraph\">Godeungeo gui is a straightforward Korean preparation that relies on the mackerel’s natural richness. Salting seasons the flesh and draws moisture from the skin; thorough drying and steady heat do the rest.</p>",
            ),
            (
                "<p class=\"wp-block-paragraph\">When it arrived &#8211; this beautifully charred, whole fish staring at me with its crispy skin glistening &#8211; I&#8217;ll admit I was a little intimidated. But that first bite? <strong>TOTAL FISH REVELATION.</strong> The skin was crispy like bacon, the flesh was buttery and flaky, and there was this incredible smoky, salty flavor that was completely different from any fish I&#8217;d ever had!</p>",
                "<p class=\"wp-block-paragraph\">For easier serving, ask the fishmonger to butterfly the mackerel or use skin-on fillets. Whole fish offers a traditional presentation, while fillets cook faster and make portioning simpler.</p>",
            ),
            (
                "<h2 class=\"wp-block-heading\">Why Your Body Will Thank You for This Fish Choice</h2>",
                "<h2 class=\"wp-block-heading\">Serving and Food-Safety Notes</h2>",
            ),
            (
                "<li><strong>Omega-3 powerhouse</strong> for heart and brain health</li>\n\n\n\n<li><strong>High-quality protein</strong> with all essential amino acids</li>\n\n\n\n<li><strong>Vitamin D</strong> for bone health and immune function</li>\n\n\n\n<li><strong>B vitamins</strong> for energy and nervous system support</li>\n\n\n\n<li><strong>Selenium</strong> for antioxidant protection</li>\n\n\n\n<li><strong>Low mercury</strong> compared to larger fish species</li>",
                "<li>Buy chilled fish from a reliable seller and keep it refrigerated until cooking.</li>\n\n\n\n<li>Cook until the thickest part is opaque and flakes easily; an instant-read thermometer should reach 145°F (63°C).</li>\n\n\n\n<li>Mackerel has many fine bones. Check each portion carefully, especially when serving children or older diners.</li>\n\n\n\n<li>Serve immediately for the crispest skin and refrigerate leftovers promptly.</li>",
            ),
        ],
        "append": """
<h2 class="wp-block-heading">Four Reliable Ways to Cook Godeungeo Gui</h2>
<ul class="wp-block-list">
<li><strong>Outdoor grill:</strong> Oil clean grates, start skin-side down over medium-high heat, and turn only when the fish releases easily.</li>
<li><strong>Skillet:</strong> Use a thin film of neutral oil over medium heat. Press a fillet gently for the first 20 seconds so the skin stays flat.</li>
<li><strong>Oven:</strong> Roast skin-side up at 425°F (220°C) until the thickest part flakes, usually 10 to 15 minutes depending on thickness. Broil briefly only if more browning is needed.</li>
<li><strong>Air fryer:</strong> Cook skin-side up at 390°F (200°C) and begin checking at 8 minutes. Avoid overcrowding so hot air can reach the skin.</li>
</ul>

<h2 class="wp-block-heading">How to Reduce Fish Odor Without Drying the Mackerel</h2>
<p class="wp-block-paragraph">Remove the dark bloodline and any remaining membrane, pat the fish very dry, and keep the cooking area well ventilated. A short salting period improves texture, but leaving salt on too long can pull out too much moisture. Citrus is best added after cooking; a long acidic marinade can soften the surface.</p>

<h2 class="wp-block-heading">Crispy-Skin Troubleshooting</h2>
<ul class="wp-block-list">
<li><strong>The fish sticks:</strong> The surface or cooking grate was not hot and oiled enough, or the fish was moved before the skin released.</li>
<li><strong>The skin is pale:</strong> Dry it more thoroughly and avoid crowding the pan.</li>
<li><strong>The flesh is dry:</strong> Begin checking early and remove the fish as soon as the thickest part is cooked.</li>
</ul>

<p class="wp-block-paragraph">For a simple Korean meal, serve the fish with rice, kimchi, and one vegetable side. The <a href="/korean-cooking-for-beginners/">Korean cooking starter plan</a> explains how to build the rest of the table.</p>
""",
    },
}

BEGINNER_GUIDE_PATH = "/korean-cooking-for-beginners/"

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


def apply_post_overrides(post: dict) -> dict:
    override = POST_OVERRIDES.get(post["slug"])
    if not override:
        return post
    updated = dict(post)
    updated["title"] = override["title"]
    updated["excerpt"] = override["excerpt"]
    content = updated.get("content", "")
    for old, new in override.get("replacements", []):
        content = content.replace(old, new)
    updated["content"] = content + override.get("append", "")
    return updated


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


def render_beginner_guide() -> str:
    canonical = SITE + BEGINNER_GUIDE_PATH
    title = "Korean Cooking for Beginners: A 5-Dish Starter Plan"
    description = (
        "Learn Korean cooking through five approachable dishes, a compact pantry, "
        "a practical cooking order, and direct links to tested step-by-step recipes."
    )
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "@id": canonical + "#article",
            "mainEntityOfPage": canonical,
            "headline": title,
            "description": description,
            "author": {
                "@type": "Organization",
                "name": "KFOOD Journal",
                "url": SITE + "/about/",
            },
            "publisher": {
                "@type": "Organization",
                "name": "KFOOD Journal",
                "url": SITE + "/",
            },
            "datePublished": "2026-07-28",
            "dateModified": "2026-07-28",
            "inLanguage": "en",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    content = f'''
<p class="wp-block-paragraph">Korean cooking becomes much easier when you stop trying to learn an entire cuisine at once. Begin with a small pantry and five dishes that teach different techniques: mixing a sauce, seasoning vegetables, simmering a broth, browning marinated meat, and managing heat.</p>

<p class="wp-block-paragraph">This plan is designed for a first week of cooking. You do not need every Korean ingredient, a crowded table of side dishes, or special cookware. Read each recipe before shopping, check labels for allergens, and adjust seasoning at the end because soy sauce, kimchi, doenjang, and gochujang vary by brand.</p>

<h2 class="wp-block-heading">The Small Korean Pantry to Buy First</h2>
<ul class="wp-block-list">
<li><strong>Short- or medium-grain rice:</strong> the neutral base that balances stronger sauces and soups.</li>
<li><strong>Ganjang (soy sauce):</strong> use the type named in a recipe when possible. Regular brewed soy sauce is the most flexible first bottle.</li>
<li><strong>Doenjang:</strong> fermented soybean paste for stews, soups, and vegetable seasoning.</li>
<li><strong>Gochujang:</strong> fermented chile paste that adds heat, sweetness, salt, and body.</li>
<li><strong>Gochugaru:</strong> Korean red pepper flakes for direct chile flavor without the thickness of gochujang.</li>
<li><strong>Sesame oil and toasted sesame seeds:</strong> fragrant finishing ingredients; a little is usually enough.</li>
<li><strong>Garlic and green onion:</strong> the everyday aromatics that appear across the five dishes below.</li>
</ul>

<p class="wp-block-paragraph">If you cook only one or two recipes, buy the ingredients for those dishes rather than the full list. Store every product according to its package directions and use clean, dry utensils for fermented pastes.</p>

<h2 class="wp-block-heading">Dish 1: Bibimbap Teaches Balance and Preparation</h2>
<p class="wp-block-paragraph"><a href="/bibimbap/">Classic bibimbap</a> is a useful first dish because the individual parts are forgiving. Prepare rice, season two or three vegetables separately, add an egg or another protein, and mix with gochujang at the table. The goal is not a perfect restaurant arrangement; it is learning how salty, sweet, spicy, fresh, and toasted flavors balance in one bowl.</p>

<p class="wp-block-paragraph">After you are comfortable with the basic bowl, try <a href="/dolsot-bibimbap/">dolsot bibimbap</a>. The hot bowl adds a second lesson: moisture control and patient heat create the crisp nurungji layer.</p>

<h2 class="wp-block-heading">Dish 2: Pajeon Teaches Batter and Pan Heat</h2>
<p class="wp-block-paragraph"><a href="/pajeon/">Pajeon</a> shows how pan temperature changes texture. Start with a thin layer of batter and enough oil to make good contact with the pan. Wait until the underside is set before turning. If the center stays soft while the outside darkens, make the next pancake thinner or lower the heat slightly.</p>

<p class="wp-block-paragraph">Serve it with a simple soy-and-vinegar dipping sauce. This is also a practical place to use leftover green onions and small amounts of vegetables from other recipes.</p>

<h2 class="wp-block-heading">Dish 3: Bulgogi Teaches Marinade Control</h2>
<p class="wp-block-paragraph"><a href="/bulgogi/">Bulgogi</a> introduces a soy-based marinade and fast cooking. Slice the meat thinly and do not overcrowd the pan. Too much liquid or too many pieces at once will steam the meat instead of browning it. Cook in batches and add delicate vegetables near the end.</p>

<p class="wp-block-paragraph">Taste the cooked marinade before adding extra sugar or soy sauce. A balanced bulgogi should be savory and lightly sweet, not covered by a thick sauce.</p>

{ad_zone("content")}

<h2 class="wp-block-heading">Dish 4: Doenjang Jjigae Teaches Layered Seasoning</h2>
<p class="wp-block-paragraph"><a href="/doenjang-jjigae/">Doenjang jjigae</a> is a compact lesson in building broth. Dissolve a modest amount of doenjang first, simmer firm vegetables until nearly tender, then add quick-cooking ingredients such as tofu and green onion. Because doenjang differs greatly by brand, make the final salt adjustment only after the stew has simmered.</p>

<p class="wp-block-paragraph">If dried anchovy is unavailable or unsuitable for your diet, kelp and dried mushrooms can provide a satisfying alternative broth. The flavor will be different, but the cooking sequence remains useful.</p>

<h2 class="wp-block-heading">Dish 5: Godeungeo Gui Teaches Timing</h2>
<p class="wp-block-paragraph"><a href="/godeungeo-gui/">Godeungeo gui</a> is deliberately simple: salt, dry the surface, and cook until the skin is crisp and the thickest part of the fish flakes. It teaches one of the most transferable kitchen habits—preparing the ingredient correctly before heat is applied.</p>

<p class="wp-block-paragraph">Use skin-on fillets if a whole fish feels difficult. Serve with rice, kimchi, and one seasoned vegetable rather than trying to prepare a large restaurant-style spread.</p>

<h2 class="wp-block-heading">A Practical Cooking Order</h2>
<ol class="wp-block-list">
<li><strong>Read the whole recipe.</strong> Note soaking, marinating, and cooling time before you begin.</li>
<li><strong>Cook rice first.</strong> It can rest covered while you prepare the main dish.</li>
<li><strong>Make cold or room-temperature components.</strong> Dipping sauces and seasoned vegetables can wait.</li>
<li><strong>Start soups and stews.</strong> Use their simmering time to prepare garnishes and wash tools.</li>
<li><strong>Cook fast items last.</strong> Pancakes, bulgogi, grilled fish, and fried eggs are best served immediately.</li>
</ol>

<h2 class="wp-block-heading">Common Beginner Mistakes</h2>
<ul class="wp-block-list">
<li><strong>Buying too many sauces:</strong> learn the role of a few staples before adding specialty products.</li>
<li><strong>Seasoning only at the beginning:</strong> fermented ingredients concentrate as they simmer, so taste again near the end.</li>
<li><strong>Substituting chile flakes one-for-one:</strong> ordinary flakes may be hotter or more bitter than gochugaru. Begin with less.</li>
<li><strong>Crowding the pan:</strong> excess moisture prevents browning in bulgogi, pancakes, and fish.</li>
<li><strong>Trying to make too many banchan:</strong> rice, one main dish, kimchi, and one vegetable side already make a complete home meal.</li>
</ul>

<h2 class="wp-block-heading">Where to Go Next</h2>
<p class="wp-block-paragraph">Once these five techniques feel familiar, choose the next recipe by method rather than difficulty. For a spicy beef broth, cook <a href="/yukgaejang/">yukgaejang</a>. For a soft-tofu stew, try <a href="/sundubu-jjigae/">sundubu jjigae</a>. For a cold noodle lesson, make <a href="/naengmyeon/">naengmyeon</a>. You can also review the broader <a href="/food-guide/">Korean food guide</a> for seasoning, meal structure, and shopping terminology.</p>
'''
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(title)} | KFOOD Journal</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:url" content="{canonical}">
  <meta name="twitter:card" content="summary">
  <script type="application/ld+json">{schema}</script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/webfontworld/scoredream/SCoreDream.css">
  <link rel="stylesheet" href="/styles.css">
  <link rel="stylesheet" href="/assets/pages.css">
  {ADSENSE_LOADER}
</head>
<body class="page-shell" data-alternate-url="/ko/food-guide/">
  <div data-site-header>{site_header("en", "/ko/food-guide/")}</div>
  <main><article class="article-shell">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>›</span><a href="/food-guide/">Food Guide</a><span>›</span><span aria-current="page">{html.escape(title)}</span></nav>
    <a class="article-back" href="/food-guide/">← Back to the food guide</a>
    <header class="article-header"><div><p class="article-kicker">KOREAN COOKING 101</p><h1 class="article-title">{html.escape(title)}</h1><p class="article-meta">2026-07-28 · KFOOD JOURNAL</p></div></header>
    <div class="article-body">{content}</div>
    <section class="related-recipes"><p class="article-kicker">START COOKING</p><div>
      <a href="/dolsot-bibimbap/"><span>01</span><strong>Dolsot Bibimbap</strong></a>
      <a href="/yukgaejang/"><span>02</span><strong>Yukgaejang</strong></a>
      <a href="/godeungeo-gui/"><span>03</span><strong>Godeungeo Gui</strong></a>
    </div></section>
  </article></main>
  <div data-site-footer>{site_footer("en")}</div>
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
    static_pages = ["/", "/recipes/", "/stories/", "/food-guide/", BEGINNER_GUIDE_PATH, "/about/", "/contact/", "/privacy/", "/ko/", "/ko/recipes/", "/ko/stories/", "/ko/food-guide/", "/ko/about/", "/ko/contact/", "/ko/privacy/"]
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
    posts = [
        apply_post_overrides(post)
        for post in json.loads(DATA_FILE.read_text(encoding="utf-8"))
    ]
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
    beginner_guide_dir = ROOT / BEGINNER_GUIDE_PATH.strip("/")
    beginner_guide_dir.mkdir(exist_ok=True)
    (beginner_guide_dir / "index.html").write_text(render_beginner_guide(), encoding="utf-8")
    write_sitemap(posts, posts_by_slug)
    (ROOT / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: https://kfood.bumkok.com/sitemap.xml\n", encoding="utf-8")
    (ROOT / "ads.txt").write_text("google.com, pub-5699330365644775, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    hydrate_static_pages()
    print(f"Generated {len(posts)} historical recipe routes and sitemap.xml")


if __name__ == "__main__":
    main()
