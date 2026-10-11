#!/usr/bin/env python3
"""HTTP-only KFOOD production audit with DNS-failure protection.

This script fetches HTML and static control files with curl. It never executes
JavaScript, so it does not load AdSense or Analytics and does not click links.

Failure policy:
1. Normal DNS/HTTPS request with bounded retries.
2. If DNS/transport fails, retry through the last known-good GitHub Pages IPs
   using curl --resolve (TLS and Host header remain kfood.bumkok.com).
3. One unverified environment failure is recorded but does not page the user.
4. A second consecutive environment failure exits non-zero for attention.
5. A real HTTP/content regression exits non-zero immediately.
"""

import argparse
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "audit-manifest.json"
DEFAULT_STATE_PATH = ROOT / ".audit-state" / "live-http-audit.json"
HOST = "kfood.bumkok.com"
SITE = "https://kfood.bumkok.com"

PRIORITY_URLS = (
    f"{SITE}/yukgaejang/",
    f"{SITE}/galbitang/",
    f"{SITE}/dolsot-bibimbap/",
    f"{SITE}/sundubu-jjigae/",
    f"{SITE}/haemultang/",
    f"{SITE}/godeungeo-gui/",
)

ADS_LINE = "google.com, pub-5699330365644775, DIRECT, f08c47fec0942fa0"
ADS_SCRIPT = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
MIN_SITEMAP_URLS = 66


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class FetchResult:
    url: str
    returncode: int
    http_code: int
    remote_ip: str
    effective_url: str
    body: bytes
    stderr: str
    resolve_ip: Optional[str] = None

    @property
    def transport_ok(self) -> bool:
        return self.returncode == 0 and self.http_code > 0


class RawHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical: Optional[str] = None
        self.noindex = False
        self.hreflangs: List[str] = []
        self.images: List[str] = []
        self.links: List[str] = []
        self.h1_count = 0
        self.script_sources: List[str] = []
        self.jsonld: List[str] = []
        self._jsonld_buffer: Optional[List[str]] = None

    def handle_starttag(self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "link":
            rel = values.get("rel", "").lower().split()
            if "canonical" in rel:
                self.canonical = values.get("href")
            if "alternate" in rel and values.get("hreflang"):
                self.hreflangs.append(values["hreflang"])
        elif tag == "meta":
            name = values.get("name", "").lower()
            if name in {"robots", "googlebot"} and "noindex" in values.get("content", "").lower():
                self.noindex = True
        elif tag == "img" and values.get("src"):
            self.images.append(values["src"])
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"])
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "script":
            if values.get("src"):
                self.script_sources.append(values["src"])
            if values.get("type", "").lower() == "application/ld+json":
                self._jsonld_buffer = []

    def handle_data(self, data: str) -> None:
        if self._jsonld_buffer is not None:
            self._jsonld_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._jsonld_buffer is not None:
            self.jsonld.append("".join(self._jsonld_buffer))
            self._jsonld_buffer = None


def load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "version": 1,
            "last_success_at": None,
            "last_known_ips": [],
            "consecutive_environment_failures": 0,
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "version": 1,
            "last_success_at": None,
            "last_known_ips": [],
            "consecutive_environment_failures": 0,
        }
    value.setdefault("version", 1)
    value.setdefault("last_success_at", None)
    value.setdefault("last_known_ips", [])
    value.setdefault("consecutive_environment_failures", 0)
    return value


def save_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def curl_fetch(url: str, resolve_ip: Optional[str] = None) -> FetchResult:
    parsed = urlparse(url)
    with tempfile.NamedTemporaryFile(prefix="kfood-http-", delete=False) as handle:
        body_path = Path(handle.name)
    command = [
        "curl",
        "--location",
        "--silent",
        "--show-error",
        "--retry",
        "2",
        "--retry-delay",
        "2",
        "--retry-all-errors",
        "--connect-timeout",
        "5",
        "--max-time",
        "15",
        "--user-agent",
        "KFOOD-HTTP-Audit/1.0 (HTTP-only; no JavaScript)",
        "--output",
        str(body_path),
        "--write-out",
        "%{http_code}\t%{remote_ip}\t%{url_effective}",
    ]
    if resolve_ip:
        port = parsed.port or 443
        command.extend(["--resolve", f"{parsed.hostname}:{port}:{resolve_ip}"])
    command.append(url)
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    body = body_path.read_bytes() if body_path.exists() else b""
    body_path.unlink(missing_ok=True)
    parts = completed.stdout.strip().split("\t", 2)
    try:
        http_code = int(parts[0]) if parts and parts[0] else 0
    except ValueError:
        http_code = 0
    remote_ip = parts[1] if len(parts) > 1 else ""
    effective_url = parts[2] if len(parts) > 2 else url
    return FetchResult(
        url=url,
        returncode=completed.returncode,
        http_code=http_code,
        remote_ip=remote_ip,
        effective_url=effective_url,
        body=body,
        stderr=completed.stderr.strip(),
        resolve_ip=resolve_ip,
    )


def fetch_through_cached_ips(url: str, ips: Iterable[str]) -> FetchResult:
    last = FetchResult(url, 6, 0, "", url, b"", "No cached IP was reachable")
    for ip in ips:
        result = curl_fetch(url, resolve_ip=ip)
        last = result
        if result.transport_ok:
            return result
    return last


def flatten_json(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from flatten_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from flatten_json(child)


def has_type(value: Dict[str, Any], wanted: str) -> bool:
    actual = value.get("@type")
    if isinstance(actual, str):
        return actual == wanted
    if isinstance(actual, list):
        return wanted in actual
    return False


def validate_recipe_schema(parser: RawHTML, url: str) -> List[str]:
    errors: List[str] = []
    objects: List[Dict[str, Any]] = []
    for payload in parser.jsonld:
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            errors.append(f"{url}: invalid JSON-LD")
            continue
        objects.extend(flatten_json(decoded))
    recipes = [item for item in objects if has_type(item, "Recipe")]
    if not recipes:
        return errors + [f"{url}: Recipe JSON-LD missing"]
    recipe = recipes[0]
    for field in ("name", "description", "image", "recipeIngredient", "recipeInstructions"):
        if not recipe.get(field):
            errors.append(f"{url}: Recipe.{field} missing")
    steps = [item for item in flatten_json(recipe.get("recipeInstructions", [])) if has_type(item, "HowToStep")]
    if not steps:
        errors.append(f"{url}: HowToStep missing")
    for index, step in enumerate(steps, 1):
        if not step.get("name") or not step.get("url"):
            errors.append(f"{url}: HowToStep {index} requires name and url")
    return errors


def validate_html(url: str, body: bytes, canonical: str, recipe: bool) -> List[str]:
    errors: List[str] = []
    text = body.decode("utf-8", errors="replace")
    parser = RawHTML()
    parser.feed(text)
    if parser.canonical != canonical:
        errors.append(f"{url}: canonical {parser.canonical!r}, expected {canonical!r}")
    if parser.noindex:
        errors.append(f"{url}: noindex detected")
    if not parser.hreflangs:
        errors.append(f"{url}: hreflang missing")
    if parser.h1_count != 1:
        errors.append(f"{url}: expected one H1, found {parser.h1_count}")
    if not parser.images:
        errors.append(f"{url}: crawlable image missing")
    if not any(ADS_SCRIPT in src for src in parser.script_sources):
        errors.append(f"{url}: AdSense script missing")
    internal_links = [
        href for href in parser.links
        if href.startswith("/") or href.startswith(SITE)
    ]
    if not internal_links:
        errors.append(f"{url}: internal links missing")
    if recipe:
        errors.extend(validate_recipe_schema(parser, url))
    return errors


def environment_failure(
    state_path: Path,
    state: Dict[str, Any],
    probe: FetchResult,
) -> int:
    failures = int(state.get("consecutive_environment_failures", 0)) + 1
    state["consecutive_environment_failures"] = failures
    state["last_check_at"] = utc_now()
    state["last_check_status"] = "environment_network_failure"
    state["last_error"] = probe.stderr or f"curl={probe.returncode}, HTTP={probe.http_code}"
    save_state(state_path, state)
    if failures < 2:
        print("DEFERRED_ENVIRONMENT_FAILURE")
        print("Public HTTP state was not verified; this is not evidence of a site outage.")
        print(f"consecutive_environment_failures={failures}")
        print(f"last_success_at={state.get('last_success_at')}")
        return 0
    print("ENVIRONMENT_FAILURE_PERSISTENT")
    print("Public HTTP state remains unverified after consecutive runs.")
    print(f"consecutive_environment_failures={failures}")
    print(f"last_success_at={state.get('last_success_at')}")
    return 20


def run(state_path: Path) -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    targets = list(manifest.get("targets", []))
    if not targets:
        print("SITE_REGRESSION")
        print("audit-manifest.json has no targets")
        return 10
    state = load_state(state_path)
    manifest_url = f"{SITE}/audit-manifest.json"
    probe = curl_fetch(manifest_url)
    mode = "normal_dns"
    selected_ip: Optional[str] = None
    if not probe.transport_ok:
        probe = fetch_through_cached_ips(manifest_url, state.get("last_known_ips", []))
        if not probe.transport_ok:
            return environment_failure(state_path, state, probe)
        mode = "cached_ip_fallback"
        selected_ip = probe.resolve_ip

    fetches: Dict[str, FetchResult] = {manifest_url: probe}
    urls = [str(item["url"]) for item in targets]
    for url in PRIORITY_URLS:
        if url not in urls:
            urls.append(url)
    for url in urls:
        if url in fetches:
            continue
        result = curl_fetch(url, resolve_ip=selected_ip) if selected_ip else curl_fetch(url)
        if not result.transport_ok and not selected_ip:
            result = fetch_through_cached_ips(url, state.get("last_known_ips", []))
        fetches[url] = result

    transport_failures = [result for result in fetches.values() if not result.transport_ok]
    if transport_failures:
        return environment_failure(state_path, state, transport_failures[0])

    errors: List[str] = []
    expected_status = {str(item["url"]): int(item.get("status", 200)) for item in targets}
    for url in PRIORITY_URLS:
        expected_status[url] = 200
    for url, result in fetches.items():
        wanted = expected_status.get(url, 200)
        if result.http_code != wanted:
            errors.append(f"{url}: HTTP {result.http_code}, expected {wanted}")

    live_manifest = fetches[manifest_url].body
    try:
        if json.loads(live_manifest.decode("utf-8")) != manifest:
            errors.append("live audit-manifest.json differs from repository")
    except (UnicodeDecodeError, json.JSONDecodeError):
        errors.append("live audit-manifest.json is invalid")

    robots = fetches[f"{SITE}/robots.txt"].body.decode("utf-8", errors="replace")
    if "User-agent: *" not in robots or "Allow: /" not in robots or f"Sitemap: {SITE}/sitemap.xml" not in robots:
        errors.append("robots.txt controls are incomplete")

    ads = fetches[f"{SITE}/ads.txt"].body.decode("utf-8", errors="replace")
    if ADS_LINE not in ads.splitlines():
        errors.append("ads.txt publisher line missing")

    sitemap = fetches[f"{SITE}/sitemap.xml"].body.decode("utf-8", errors="replace")
    sitemap_count = len(re.findall(r"<loc>", sitemap))
    if sitemap_count < MIN_SITEMAP_URLS:
        errors.append(f"sitemap has {sitemap_count} URLs; expected at least {MIN_SITEMAP_URLS}")

    for item in targets:
        url = str(item["url"])
        if not url.endswith((".txt", ".xml", ".json")):
            canonical = str(item.get("canonical") or url)
            errors.extend(validate_html(url, fetches[url].body, canonical, recipe=False))
    for url in PRIORITY_URLS:
        errors.extend(validate_html(url, fetches[url].body, url, recipe=True))

    if errors:
        state["last_check_at"] = utc_now()
        state["last_check_status"] = "site_regression"
        state["last_errors"] = errors
        save_state(state_path, state)
        print("SITE_REGRESSION")
        for error in errors:
            print(f"- {error}")
        return 10

    ips = set(str(ip) for ip in state.get("last_known_ips", []) if ip)
    ips.update(result.remote_ip for result in fetches.values() if result.remote_ip)
    state.update(
        {
            "version": 1,
            "last_success_at": utc_now(),
            "last_check_at": utc_now(),
            "last_check_status": "success_dns_fallback" if mode == "cached_ip_fallback" else "success",
            "last_known_ips": sorted(ips),
            "consecutive_environment_failures": 0,
            "last_error": None,
            "last_errors": [],
            "checked_urls": len(fetches),
            "sitemap_urls": sitemap_count,
        }
    )
    save_state(state_path, state)
    print("SUCCESS_DNS_FALLBACK" if mode == "cached_ip_fallback" else "SUCCESS")
    print(f"checked_urls={len(fetches)}")
    print(f"sitemap_urls={sitemap_count}")
    print(f"cached_ips={','.join(state['last_known_ips'])}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    args = parser.parse_args()
    return run(args.state)


if __name__ == "__main__":
    raise SystemExit(main())
