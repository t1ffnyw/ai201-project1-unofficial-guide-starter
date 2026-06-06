"""Chunk the scraped documents/*.txt files into chunks.jsonl for the embedding stage.

Two document types are chunked differently (see planning.md > Chunking Strategy):
  - reddit  : each comment is the natural unit (1 comment = 1 chunk). The post block
              (title + selftext) is its own chunk. Any unit over the cap is recursively
              split so no chunk dwarfs the rest.
  - article : one chunk per restaurant section (a short "Name" line followed by a
              description paragraph). Sections over the cap are recursively split, with
              the restaurant name re-prepended so context survives the boundary.

Every input file starts with a 5-line header written by scrape.py:
    Source: ...
    Type: reddit | article
    Category: ...
    URL: ...
    ---
which supplies the metadata attached to each chunk.

A short context line (e.g. "[ethiopian | Reddit: Ethiopian] ") is prepended to each
chunk's text so the embedding captures the source/cuisine without a separate field lookup.

Usage:
    python chunk.py            # chunk everything in documents/ -> documents/chunks.jsonl
"""

import json
import re
import statistics
import sys
from pathlib import Path

# Use UTF-8 for stdout so the summary glyphs don't crash on the Windows cp1252 console.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "documents"
OUTPUT_PATH = DOCS_DIR / "chunks.jsonl"

ARTICLE_TARGET = 450  # preferred chunk size for articles (chars); strategy target is 300-500
ARTICLE_CAP = 600     # article sections over this get recursively split
REDDIT_CAP = 1200     # most Reddit comments fit under this; only split if larger
OVERLAP = 75          # carried between pieces — only when a unit is recursively split
SEPARATORS = ["\n\n", "\n", ". ", " "]

MIN_COMMENT_LEN = 50  # filter out short noise comments (e.g. "This.", "Great, thanks!")
SCORE_THRESHOLD = 2   # filter out downvoted / zero-engagement comments

COMMENTS_MARKER = "--- Comments ---"
# A comment line looks like: "[author, 12 pts] body..." or "[author] body...",
# possibly indented 2 spaces per reply depth.
COMMENT_RE = re.compile(r"^(?P<indent>\s*)\[(?P<author>[^\],]+?)(?:,\s*(?P<score>-?\d+)\s*pts)?\]\s*(?P<body>.*)$")
SKIP_BODIES = {"[deleted]", "[removed]", ""}

# Article markdown-header patterns (e.g. "#### [Charleston](url)" or "### Foraged")
_MD_HEADER_RE = re.compile(r"^#{1,6}\s+")
_MD_LINK_RE   = re.compile(r"\[([^\]]+)\]\([^)]+\)")

# Curated set of verified restaurant names used to tag Reddit chunks.
# Whole-phrase matching (case/apostrophe insensitive) avoids the false positives
# produced by a pure regex approach ("So I'd", "The Chicken", etc.).
KNOWN_RESTAURANTS = {
    "Alma Cocina Latina", "Ammoora", "Ananda", "Azumi",
    "Baby's On Fire", "Blacksauce Kitchen", "Blue Moon Cafe",
    "Bunny's Buckets & Bubbles",
    "Café Dear Leon", "Cece's of Roland Park", "Chachi's", "Chiyo Sushi",
    "Charleston", "Cinghiale", "Clavel", "Cookhouse", "Cosima", "Costiera",
    "Dangerously Delicious Pies", "Dooby's", "Dylan's Oyster Cellar",
    "Ekiben", "Ethel's Creole Kitchen",
    "Faidley's Seafood", "Foraged",
    "Gertrude's", "Golden West Café", "Gunther & Co.",
    "Hersh's",
    "Jimmy's Famous Seafood", "Johnny Rad's",
    "Koco's Pub", "Kooper's Tavern",
    "La Cuchara", "La Scala Ristorante Italiano", "Land of Kush",
    "Le Comptoir du Vin", "Linwoods", "Little Donna's", "Loch Bar",
    "LP Steamers",
    "Maggie's Farm", "Magdalena Restaurant", "Mama's on the Half Shell",
    "Marta", "Mera Kitchen Collective",
    "NiHao", "Nick's Fish House",
    "Papermoon Diner", "Peter's Inn", "Petit Louis Bistro", "Phillips Seafood",
    "Puerto 511",
    "Ramen Utsuke", "Restaurante Tio Pepe", "Rocket to Venus",
    "Rooted Rotisserie", "Rusty Scupper",
    "SoBo Cafe", "Sotto Sopra",
    "Tagliata", "Tapas Teatro", "Thai Street",
    "Thames Street Oyster House", "The Black Olive", "The Bluebird Cocktail Room",
    "The Bygone", "The Charmery", "The Choptank", "The Corner Pantry",
    "The Dara", "The Duchess", "The Elk Room", "The Empanada Lady",
    "The Food Market", "The Helmand", "The Local Fry", "The Milton Inn",
    "The Prime Rib", "The Urban Oyster", "The Wren",
    "True Chesapeake",
    "W.C. Harlan", "Woodberry Kitchen", "Woodberry Tavern", "Wye Oak Tavern",
}

# Normalise text for matching: lowercase + remove apostrophes/curly quotes.
_APOSTROPHE_RE = re.compile(r"['\u2019\u2018`]")


def parse_document(path: Path):
    """Split a scraped file into its header metadata dict and body text."""
    text = path.read_text(encoding="utf-8")
    meta = {"source": "", "type": "", "category": "", "url": ""}
    body = text
    if "\n---\n" in text:
        header, body = text.split("\n---\n", 1)
        for line in header.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            if key in meta:
                meta[key] = value.strip()
    return meta, body.strip()


def _overlap_tail(text, overlap):
    """Last `overlap` chars of text, trimmed forward to a word boundary (no mid-word start)."""
    if not overlap:
        return ""
    tail = text[-overlap:]
    space = tail.find(" ")
    return tail[space + 1:] if space != -1 else tail


def recursive_split(text, target=ARTICLE_TARGET, overlap=OVERLAP):
    """Greedily split text into ~target-sized chunks, trying separators in order.

    Overlap is carried from the tail of one chunk into the head of the next. This is the
    only place overlap is applied; whole units under the cap are emitted verbatim.
    """
    text = text.strip()
    if len(text) <= target:
        return [text] if text else []

    # Pick the first separator that actually appears; fall back to a hard char split.
    sep = next((s for s in SEPARATORS if s in text), None)
    if sep is None:
        return [text[i:i + target] for i in range(0, len(text), max(1, target - overlap))]

    # Break into units no larger than target, recursing on any oversized piece first.
    units = []
    for piece in text.split(sep):
        piece = piece.strip()
        if not piece:
            continue
        if len(piece) > target:
            units.extend(recursive_split(piece, target, overlap))
        else:
            units.append(piece)

    # Greedily recombine units up to target, carrying a word-boundary overlap forward.
    chunks, current = [], ""
    for unit in units:
        candidate = unit if not current else current + sep + unit
        if len(candidate) <= target:
            current = candidate
        elif current:
            chunks.append(current)
            tail = _overlap_tail(current, overlap)
            # Skip prepending the tail when the unit already starts with it —
            # that happens when an inner recursive call already embedded the overlap,
            # and naively prepending again produces duplicated phrases.
            if tail and unit.startswith(tail):
                current = unit
            else:
                current = f"{tail} {unit}".strip() if tail else unit
        else:
            current = unit
    if current:
        chunks.append(current)
    return [c.strip() for c in chunks if c.strip()]


def context_prefix(meta):
    """Short category tag prepended so the embedding captures cuisine/topic context.

    Source name and type are already in the JSON metadata fields; repeating them here
    wastes ~10% of the chunk budget on every record.
    """
    return f"[{meta['category']}] "


def make_chunk(doc_id, n, meta, body, *, restaurant=None, author=None, score=None, is_question=False):
    """Assemble one chunk record with metadata-prefixed text.

    is_question=True marks the OP post so retrieval can down-rank or skip it —
    a question is semantically close to a query and would otherwise crowd out answers.
    """
    return {
        "id": f"{doc_id}_{n}",
        "text": context_prefix(meta) + body,
        "source": meta["source"],
        "type": meta["type"],
        "category": meta["category"],
        "url": meta["url"],
        "restaurant": restaurant,
        "author": author,
        "score": score,
        "is_question": is_question,
    }


def _normalize_name(s):
    """Lowercase and strip apostrophes/curly quotes for fuzzy name matching."""
    return _APOSTROPHE_RE.sub("", s.lower())


def _extract_reddit_restaurants(text):
    """Match comment text against the KNOWN_RESTAURANTS set.

    Uses whole-phrase, apostrophe-insensitive lookup so "Seconding Peters Inn"
    still matches "Peter's Inn" without picking up sentence fragments or menu
    items the way the old regex approach did.
    """
    text_norm = _normalize_name(text)
    found = [name for name in KNOWN_RESTAURANTS if _normalize_name(name) in text_norm]
    return ", ".join(found[:3]) if found else None


def chunk_reddit(doc_id, meta, body):
    """Post block + one chunk per comment; only split comments that exceed REDDIT_CAP."""
    chunks = []
    n = 0
    if COMMENTS_MARKER in body:
        post, comment_block = body.split(COMMENTS_MARKER, 1)
    else:
        post, comment_block = body, ""

    # OP post (title + selftext): tagged is_question=True so retrieval can filter it out.
    # The post is semantically close to a query and would otherwise crowd out answers.
    post = post.strip()
    if post:
        for piece in recursive_split(post, target=REDDIT_CAP):
            chunks.append(make_chunk(doc_id, n, meta, piece, author="OP", is_question=True))
            n += 1

    # Accumulate each comment as a full block: a "[author, N pts]" line starts a new
    # comment; following lines (multi-paragraph bodies) belong to it until the next header.
    comments = []  # list of (author, score, body)
    current = None
    for line in comment_block.splitlines():
        m = COMMENT_RE.match(line)
        if m:
            if current:
                comments.append(current)
            author = m.group("author").strip()
            score = int(m.group("score")) if m.group("score") is not None else None
            current = [author, score, m.group("body").strip()]
        elif current is not None and line.strip():
            current[2] = (current[2] + "\n" + line.strip()).strip()
    if current:
        comments.append(current)

    # One chunk per comment. Only split if the comment exceeds REDDIT_CAP so that
    # substantive 500-800 char comments are kept whole.
    for author, score, body_text in comments:
        if body_text in SKIP_BODIES:
            continue
        if len(body_text) < MIN_COMMENT_LEN:
            continue
        if score is not None and score < SCORE_THRESHOLD:
            continue
        restaurant = _extract_reddit_restaurants(body_text)
        for piece in recursive_split(body_text, target=REDDIT_CAP):
            chunks.append(make_chunk(doc_id, n, meta, piece, author=author, score=score,
                                     restaurant=restaurant))
            n += 1
    return chunks


def _extract_markdown_name(line):
    """Return the restaurant name from a markdown header line, or None.

    Handles both plain headers ("#### Foraged") and linked headers
    ("#### [Charleston](https://charlestonrestaurant.com/)").
    Returns None for image captions and other long header lines whose text
    is clearly not a restaurant name (length > 80 chars, or contains ";").
    """
    if not _MD_HEADER_RE.match(line):
        return None
    rest = _MD_HEADER_RE.sub("", line).strip()
    m = _MD_LINK_RE.match(rest)
    name = m.group(1) if m else (rest or None)
    if name and (len(name) > 80 or ";" in name):
        return None
    # "By the Numbers" entries like "#### 350" or "#### 24,000"
    try:
        float(name.replace(",", ""))
        return None
    except (ValueError, AttributeError):
        pass
    return name


# Words that mark category/section headers rather than restaurant names.
_SECTION_KEYWORDS = frozenset({
    "Restaurants", "Suites", "Spas", "Activities", "Lounges", "Dining",
    "Hotels", "Bars", "Clubs",
})

# Explicit short strings that pass other checks but are not restaurant names.
_SKIP_NAMES = frozenset({
    "Forever Dishes", "Read More", "Swap Out the Swine",
    "Last Updated", "By the Numbers",
})


def _looks_like_name(line):
    """Heuristic: a short, non-terminal line that introduces a restaurant section."""
    line = line.strip()
    if not line or len(line) > 60:
        return False
    if line.endswith((".", "!", "?", ":")):
        return False
    if line.startswith("#") or line.startswith("*"):
        return False
    # All-caps lines are neighborhood/section headers (HARBOR EAST, MEET THE CHEF, etc.)
    if line.replace(" ", "").replace("'", "").isupper():
        return False
    # Category/section headers: "Romantic Restaurants", "Serene Spas", "Bolton Hill Restaurants"…
    if set(line.split()) & _SECTION_KEYWORDS:
        return False
    # "Dish at Restaurant" lines and activity lines ("Stargaze at …", "Explore … by boat")
    if " at " in line:
        return False
    # Chef attribution lines: "Carlos Raba, chef of Nana"
    if "chef of" in line.lower():
        return False
    # Explicit edge-case skip list
    if any(line.startswith(skip) for skip in _SKIP_NAMES):
        return False
    # Mostly a proper-noun heading: starts uppercase, not a full sentence.
    return line[0].isupper() and len(line.split()) <= 8


def chunk_article(doc_id, meta, body):
    """One chunk per restaurant section; sections over the cap recursively split."""
    # Scan line by line: a "name" line (short, title-like, no terminal punctuation) opens a
    # new restaurant section; the lines after it are its description, until the next name.
    # This handles both blank-line-separated layouts and single-newline lists (crab cakes),
    # where every restaurant name and description sit on adjacent lines in one paragraph.
    sections = []  # list of (name_or_None, [body lines])
    name, desc = None, []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("[extracted via"):
            continue
        # Horizontal dividers (e.g. "* * *") close the current section without
        # opening a named one — content after the divider becomes a fresh unnamed
        # section so scraper-boundary gaps (Clavel, Duchess) don't inherit the
        # preceding restaurant's name.
        if stripped in ("* * *", "---", "* * * * *"):
            if name is not None or desc:
                sections.append((name, desc))
            name, desc = None, []
            continue
        md_name = _extract_markdown_name(stripped)
        if md_name:
            if name is not None or desc:
                sections.append((name, desc))
            name, desc = md_name, []
        elif _looks_like_name(stripped):
            if name is not None or desc:
                sections.append((name, desc))
            name, desc = stripped, []
        else:
            desc.append(stripped)
    if name is not None or desc:
        sections.append((name, desc))

    # Assemble each section's text (name kept as the first line so the leading split piece
    # already carries it). Drop name-only sections that never got a description.
    sections = [
        (name, "\n".join(([name] if name else []) + desc).strip())
        for name, desc in sections
        if desc  # drop empty stubs produced by divider resets or name-only lines
    ]

    if not sections:
        # No structure detected — fall back to recursive split of the whole body.
        sections = [(None, body)]

    # The metadata prefix is added to every chunk's text, so reserve room for it when
    # deciding whether a section fits under the cap.
    reserve = len(context_prefix(meta))
    chunks, n = [], 0
    for name, text in sections:
        if len(text) <= ARTICLE_CAP - reserve:
            chunks.append(make_chunk(doc_id, n, meta, text, restaurant=name))
            n += 1
        else:
            # Shrink the split target so the final text (context prefix + re-prepended
            # name + piece + overlap) still fits under the cap.
            name_prefix = f"{name}: " if name else ""
            target = min(ARTICLE_TARGET, ARTICLE_CAP - reserve - len(name_prefix) - OVERLAP)
            for piece in recursive_split(text, target=target):
                # Re-prepend the name so context survives the split boundary.
                if name and not piece.startswith(name):
                    piece = f"{name_prefix}{piece}"
                chunks.append(make_chunk(doc_id, n, meta, piece, restaurant=name))
                n += 1
    return chunks


def main():
    files = sorted(DOCS_DIR.glob("*.txt"))
    if not files:
        print(f"No .txt files found in {DOCS_DIR}/ — run scrape.py first.")
        return 1

    all_chunks = []
    per_type = {"reddit": 0, "article": 0}
    for path in files:
        # doc_id = leading number of the filename (e.g. "18" from "18_ethiopian.txt").
        doc_id = path.stem.split("_", 1)[0]
        meta, body = parse_document(path)
        if meta["type"] == "reddit":
            chunks = chunk_reddit(doc_id, meta, body)
        elif meta["type"] == "article":
            chunks = chunk_article(doc_id, meta, body)
        else:
            print(f"  [skip] {path.name} — unknown type {meta['type']!r}")
            continue
        per_type[meta["type"]] = per_type.get(meta["type"], 0) + len(chunks)
        all_chunks.extend(chunks)
        print(f"  [ok]   {path.name:48s} -> {len(chunks):3d} chunks")

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    lengths = [len(c["text"]) for c in all_chunks]
    over_article_target = sum(1 for n in lengths if n > ARTICLE_TARGET)
    over_reddit_cap = sum(1 for n in lengths if n > REDDIT_CAP)
    print(f"\nWrote {len(all_chunks)} chunks -> {OUTPUT_PATH}")
    print(f"  by type: reddit={per_type['reddit']}, article={per_type['article']}")
    if lengths:
        print(f"  chunk length: min={min(lengths)} median={int(statistics.median(lengths))} max={max(lengths)}")
        print(f"  over {ARTICLE_TARGET}-char article target: {over_article_target}  |  over {REDDIT_CAP}-char Reddit cap: {over_reddit_cap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
