"""Scrape the planning.md Documents sources into clean .txt files for the RAG pipeline.

Two source types are handled differently:
  - reddit  : Reddit hard-blocks unauthenticated programmatic access, so these are read
              from locally-saved JSON files in raw/{id:02d}.json. To produce one: while
              logged into Reddit in your browser, open the thread URL with ".json" appended
              and save the response as raw/{id:02d}.json. The JSON is the post + full comment
              tree as plain-text/markdown fields (no HTML cleaning needed).
  - article : fetched via trafilatura, which extracts the main body and strips nav menus,
              cookie banners, ads, footers, share/Read-more boilerplate automatically.
              Falls back to the r.jina.ai reader (for bot-protected pages) and then a
              BeautifulSoup get_text() pass if trafilatura returns nothing.

Each source becomes documents/{id:02d}_{slug}.txt with a small attribution header so the
later retrieval stage can cite where a chunk came from.

Usage:
    python scrape.py            # scrape everything (reddit needs raw/*.json present)
    python scrape.py --reddit-urls   # just print the .json URLs to save for the manual step
"""

import json
import re
import sys
import time
from pathlib import Path

import requests
import trafilatura
from bs4 import BeautifulSoup

# Use UTF-8 for stdout so the summary's ✓/✗ don't crash on the Windows cp1252 console.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "documents"
RAW_DIR = ROOT / "raw"  # where manually-saved Reddit JSON files live
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 60
POLITE_DELAY = 2  # seconds between network requests

# Source registry — mirrors the Documents table in planning.md.
# `category` is coarse metadata that the later chunking stage can prepend to chunks.
SOURCES = [
    {"id": 1,  "type": "reddit",  "category": "general",         "name": "Restaurant Recommendations for Chef",            "url": "https://www.reddit.com/r/baltimore/comments/1e1reaf/restaurant_recommendations_needed_for_my_visiting/"},
    {"id": 2,  "type": "reddit",  "category": "fine_dining",     "name": "Fine Dining Recommendations",                     "url": "https://www.reddit.com/r/baltimore/comments/1q0mh87/fine_dining_recs/"},
    {"id": 3,  "type": "reddit",  "category": "general",         "name": "Underrated Restaurants",                          "url": "https://www.reddit.com/r/baltimore/comments/1mp82pl/what_restaurant_in_baltimore_doesnt_get_much_hype/"},
    {"id": 4,  "type": "reddit",  "category": "general",         "name": "Best Dinner Spots",                               "url": "https://www.reddit.com/r/baltimore/comments/1tbc2re/best_dinner_spots/"},
    {"id": 5,  "type": "reddit",  "category": "general",         "name": "Best Restaurants",                                "url": "https://www.reddit.com/r/baltimore/comments/1rl39z1/best_restaurants_in_baltimore/"},
    {"id": 6,  "type": "reddit",  "category": "mexican",         "name": "Mexican Restaurants",                             "url": "https://www.reddit.com/r/baltimore/comments/1tf9p5q/striking_out_on_google_anyone_know_any_mexican/"},
    {"id": 7,  "type": "reddit",  "category": "family",          "name": "Dinner with Kids (Fells Point)",                  "url": "https://www.reddit.com/r/baltimore/comments/1nekd3b/best_place_to_grab_dinner_with_kids_innear_fells/"},
    {"id": 8,  "type": "reddit",  "category": "jamaican",        "name": "Jamaican Restaurants",                            "url": "https://www.reddit.com/r/baltimore/comments/1rxh8ur/what_are_the_best_jamaican_restaurants/"},
    {"id": 9,  "type": "reddit",  "category": "fine_dining",     "name": "Michelin Worthy Restaurants",                     "url": "https://www.reddit.com/r/baltimore/comments/1qomnti/who_are_your_michelin_worthy_restaurants_in_the/"},
    {"id": 10, "type": "article", "category": "general",         "name": "DC Eater — Essential Restaurants",                "url": "https://dc.eater.com/maps/best-bars-restaurants-bakeries-baltimore-dining-guide-38"},
    {"id": 11, "type": "article", "category": "general",         "name": "Baltimore Magazine — Best Restaurants 2026",      "url": "https://www.baltimoremagazine.com/section/fooddrink/best-restaurants-baltimore-2026/"},
    {"id": 12, "type": "article", "category": "general",         "name": "The Baltimore Banner — Chef Recommendations",     "url": "https://www.thebanner.com/culture/food-drink/baltimore-county-chefs-restaurant-recommendations-OCJ2TU5XL5AMXJDWUUFJ2LRLRU/"},
    {"id": 13, "type": "article", "category": "neighborhood",    "name": "Like the Tea Eats — Best by Neighborhood",        "url": "https://liketheteaeats.com/best-baltimore-restaurants/"},
    {"id": 14, "type": "article", "category": "waterfront",      "name": "Baltimore.org — Waterfront Dining",               "url": "https://baltimore.org/what-to-do/where-to-eat/waterfront-dining-in-baltimore/"},
    {"id": 15, "type": "article", "category": "seafood",         "name": "Baltimore.org — Best Seafood",                    "url": "https://baltimore.org/what-to-do/where-to-find-baltimores-best-seafood/"},
    {"id": 16, "type": "reddit",  "category": "seafood",         "name": "Seafood",                                         "url": "https://www.reddit.com/r/baltimore/comments/18jrk5j/best_seafood_in_town/"},
    {"id": 17, "type": "reddit",  "category": "italian",         "name": "Italian",                                         "url": "https://www.reddit.com/r/baltimore/comments/1l6evp0/authentic_italian_food/"},
    {"id": 18, "type": "reddit",  "category": "ethiopian",       "name": "Ethiopian",                                       "url": "https://www.reddit.com/r/baltimore/comments/1fzyxf8/ethiopian_recommendations/"},
    {"id": 19, "type": "reddit",  "category": "asian",           "name": "Asian / Asian Fusion",                            "url": "https://www.reddit.com/r/baltimore/comments/1mifzti/any_good_asianasian_fusion_spots/"},
    {"id": 20, "type": "article", "category": "asian",           "name": "Baltimore.org — Asian-Owned Restaurants",         "url": "https://baltimore.org/what-to-do/where-to-eat/asian-owned-restaurants-in-baltimore/"},
    {"id": 21, "type": "article", "category": "vegan",           "name": "Baltimore.org — Vegan & Vegetarian",              "url": "https://baltimore.org/what-to-do/vegetarian-vegan-restaurants-in-baltimore/"},
    {"id": 22, "type": "article", "category": "budget",          "name": "Baltimore.org — Budget Friendly",                 "url": "https://baltimore.org/what-to-do/where-to-eat/budget-friendly-baltimore-restaurants/"},
    {"id": 23, "type": "article", "category": "international",    "name": "Baltimore.org — International Dining",             "url": "https://baltimore.org/what-to-do/international-dining-in-baltimore/"},
    {"id": 24, "type": "article", "category": "breakfast_brunch", "name": "Baltimore.org — Breakfast & Brunch",             "url": "https://baltimore.org/what-to-do/best-breakfast-and-brunch-spots-in-baltimore/"},
    {"id": 25, "type": "article", "category": "crab_cakes",      "name": "Baltimore.org — Crab Cakes",                      "url": "https://baltimore.org/what-to-do/where-to-eat/top-eateries-to-enjoy-authentic-baltimore-crab-cakes/"},
    {"id": 26, "type": "article", "category": "date_night",      "name": "Baltimore.org — Date Night",                      "url": "https://baltimore.org/what-to-do/baltimores-date-night-destinations/"},
]

SKIP_BODIES = {"[deleted]", "[removed]", ""}


def slugify(name: str) -> str:
    """Turn a source name into a filesystem-safe slug."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _walk_comments(children, lines, depth=0):
    """Recursively collect comment bodies from a Reddit comment listing."""
    for child in children:
        if child.get("kind") != "t1":  # t1 = comment; skip "more" stubs
            continue
        data = child.get("data", {})
        body = (data.get("body") or "").strip()
        if body and body not in SKIP_BODIES:
            author = data.get("author") or "unknown"
            score = data.get("score")
            indent = "  " * depth
            meta = f"[{author}" + (f", {score} pts" if score is not None else "") + "]"
            lines.append(f"{indent}{meta} {body}")
        replies = data.get("replies")
        if isinstance(replies, dict):
            _walk_comments(replies.get("data", {}).get("children", []), lines, depth + 1)


def reddit_json_url(url: str) -> str:
    """The URL to open (while logged in) and save for the manual step."""
    return url.split("?")[0].rstrip("/") + "/.json"


def scrape_reddit(source: dict) -> str:
    """Parse a manually-saved Reddit thread JSON (raw/{id}.json) into post + comments text."""
    # accept either zero-padded (01.json) or plain (1.json) names
    raw_path = RAW_DIR / f"{source['id']:02d}.json"
    if not raw_path.exists():
        raw_path = RAW_DIR / f"{source['id']}.json"
    if not raw_path.exists():
        raise FileNotFoundError(
            f"missing {raw_path.name} — save {reddit_json_url(source['url'])} "
            f"(while logged into Reddit) into raw/"
        )
    listings = json.loads(raw_path.read_text(encoding="utf-8"))

    post = listings[0]["data"]["children"][0]["data"]
    lines = [post.get("title", "").strip()]
    selftext = (post.get("selftext") or "").strip()
    if selftext and selftext not in SKIP_BODIES:
        lines.append("")
        lines.append(selftext)

    lines.append("")
    lines.append("--- Comments ---")
    comments = listings[1]["data"]["children"]
    _walk_comments(comments, lines)

    return "\n".join(lines).strip()


def _jina_fallback(url: str) -> str:
    """Readability proxy that renders + extracts main content; handles bot-protected pages."""
    resp = requests.get(
        "https://r.jina.ai/" + url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    text = resp.text
    # Strip the reader's "Title:/URL Source:/Markdown Content:" preamble if present.
    marker = "Markdown Content:"
    if marker in text:
        text = text.split(marker, 1)[1]
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)  # drop markdown image embeds
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # collapse the gaps they leave
    return text.strip()


def _bs4_fallback(url: str) -> str:
    """Last-resort extraction: strip obvious boilerplate tags and take the text."""
    resp = requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # collapse runs of blank lines
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()


def scrape_article(url: str) -> str:
    """Extract clean article body with trafilatura, falling back to Jina then BeautifulSoup."""
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        )
        if text and text.strip():
            return text.strip()

    # trafilatura came back empty (e.g. bot-protected / JS page) — try the reader proxy.
    try:
        text = _jina_fallback(url)
        if text and len(text) > 200 and "you've been blocked" not in text.lower():
            return "[extracted via r.jina.ai reader]\n\n" + text
    except requests.RequestException:
        pass

    # last resort: raw HTML with boilerplate tags stripped.
    text = _bs4_fallback(url)
    if not text:
        raise ValueError("no content extracted (trafilatura + jina + bs4 all empty)")
    return "[extracted via bs4 fallback]\n\n" + text


def write_document(source: dict, body: str) -> Path:
    """Write the attribution header + body to documents/{id}_{slug}.txt."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{source['id']:02d}_{slugify(source['name'])}.txt"
    path = DOCS_DIR / filename
    header = (
        f"Source: {source['name']}\n"
        f"Type: {source['type']}\n"
        f"Category: {source['category']}\n"
        f"URL: {source['url']}\n"
        "---\n\n"
    )
    path.write_text(header + body + "\n", encoding="utf-8")
    return path


def print_reddit_urls() -> int:
    """Print the .json URLs to save into raw/ for the manual Reddit step."""
    print("Save each of these (while logged into Reddit) as raw/{id}.json:\n")
    for s in SOURCES:
        if s["type"] == "reddit":
            print(f"  raw/{s['id']:02d}.json   <-  {reddit_json_url(s['url'])}")
    return 0


def main() -> int:
    if "--reddit-urls" in sys.argv:
        return print_reddit_urls()

    results = []  # (source, status, info) where status in {"ok", "skip", "fail"}
    for source in SOURCES:
        is_reddit = source["type"] == "reddit"
        try:
            body = scrape_reddit(source) if is_reddit else scrape_article(source["url"])
            if not body.strip():
                raise ValueError("empty body")
            path = write_document(source, body)
            results.append((source, "ok", f"{len(body)} chars -> {path.name}"))
            print(f"  [ok]   {source['id']:02d} {source['name']} ({len(body)} chars)")
        except FileNotFoundError as exc:
            # Reddit raw file not saved yet — expected, not a hard failure.
            results.append((source, "skip", str(exc)))
            print(f"  [skip] {source['id']:02d} {source['name']} — {exc}")
        except Exception as exc:  # noqa: BLE001 - one failure shouldn't abort the run
            results.append((source, "fail", str(exc)))
            print(f"  [FAIL] {source['id']:02d} {source['name']} — {exc}")
        if not is_reddit:
            time.sleep(POLITE_DELAY)  # only network sources need throttling

    ok = sum(1 for _, status, _ in results if status == "ok")
    print(f"\nDone: {ok}/{len(results)} sources scraped into {DOCS_DIR}/")

    skipped = [(s, info) for s, status, info in results if status == "skip"]
    if skipped:
        print(f"\nSkipped {len(skipped)} Reddit thread(s) — save their JSON, then re-run "
              f"(see `python scrape.py --reddit-urls`):")
        for s, info in skipped:
            print(f"  - {s['id']:02d} {s['name']}")

    failures = [(s, info) for s, status, info in results if status == "fail"]
    if failures:
        print("\nFailed sources (handle manually or re-run):")
        for s, info in failures:
            print(f"  - {s['id']:02d} {s['name']}: {info}")

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
