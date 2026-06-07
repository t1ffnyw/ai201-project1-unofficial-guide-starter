"""Embed chunked documents and retrieve relevant chunks via ChromaDB.

Pipeline stage (see planning.md > Retrieval Approach):
  1. Load chunks from documents/chunks.jsonl (output of chunk.py)
  2. Embed with sentence-transformers (all-MiniLM-L6-v2, 384-dim vectors)
  3. Store vectors + metadata in a local ChromaDB collection (cosine similarity)
  4. retrieve(query) detects category keywords, searches matching metadata tiers,
     reranks with restaurant and keyword bonuses, and returns top-k matches

Usage:
    python retrieval.py store              # embed + store all chunks
    python retrieval.py store --reset      # wipe collection and rebuild
    python retrieval.py query "Where can I get the best crab cakes in Baltimore?"
"""

import argparse
import json
import re
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

ROOT = Path(__file__).parent
MODEL_NAME = "all-MiniLM-L6-v2"
CHUNKS_PATH = ROOT / "documents" / "chunks.jsonl"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION_NAME = "baltimore_restaurants"
TOP_K = 5
BATCH_SIZE = 64
CANDIDATE_MULTIPLIER = 4   # fetch extra candidates before reranking
CATEGORY_MATCH_BONUS = 0.10  # used when mixing category + general pools
RESTAURANT_BONUS = 0.04      # subtract when restaurant field is populated
KEYWORD_BONUS = 0.06         # max subtract for query keyword overlap in chunk text

QUERY_STOPWORDS = frozenset({
    "a", "an", "the", "in", "for", "to", "of", "where", "can", "i", "get", "find",
    "good", "best", "some", "what", "are", "is", "near", "with", "and", "or", "at",
    "my", "me", "you", "that", "this", "how", "do", "does", "any", "there", "about",
})

# Query keyword → chunk category. Order matters: first match wins for primary category.
# CATEGORY_ALSO adds secondary categories to search (e.g. crab cakes → seafood too).
CATEGORY_TRIGGERS = [
    ("budget", ("budget-friendly", "budget friendly", "affordable", "cheap eats", "low-cost")),
    ("ethiopian", ("ethiopian",)),
    ("family", ("family-friendly", "family friendly", "with kids", "kid-friendly",
                "kid friendly", "children")),
    ("date_night", ("date night", "romantic dinner", "romantic restaurant", "anniversary")),
    ("fine_dining", ("fine dining", "michelin", "upscale", "fancy restaurant")),
    ("crab_cakes", ("crab cake", "crab cakes")),
    ("seafood", ("seafood", "oyster", "oysters", "crab house", "steamed crabs")),
    ("mexican", ("mexican", "taco", "taqueria", "tacos")),
    ("italian", ("italian", "pasta", "pizzeria")),
    ("jamaican", ("jamaican",)),
    ("vegan", ("vegan", "vegetarian", "plant-based")),
    ("asian", ("asian", "chinese", "sichuan", "dim sum", "japanese", "sushi", "ramen")),
    ("breakfast_brunch", ("breakfast", "brunch")),
    ("waterfront", ("waterfront",)),
    ("neighborhood", ("fells point", "canton", "hampden", "neighborhood")),
]

CATEGORY_ALSO = {
    "crab_cakes": ("seafood",),
    "ethiopian": ("international",),
    "family": ("neighborhood",),
    "date_night": ("fine_dining",),
    "budget": (),  # keep budget queries focused on doc 22
}

_model = None
_client = None


def load_chunks(path=CHUNKS_PATH):
    """Load chunk records from a JSONL file produced by chunk.py."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run `python chunk.py` first to generate chunks."
        )
    chunks = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def _get_model():
    """Lazy-load and cache the embedding model singleton."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_client():
    """Lazy-load and cache the ChromaDB persistent client."""
    global _client
    if _client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


def _get_collection():
    """Open (or create) the ChromaDB collection with cosine distance."""
    client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _clean_metadata(chunk):
    """Convert chunk metadata to ChromaDB-safe values (no None)."""
    return {
        "source": chunk["source"],
        "type": chunk["type"],
        "category": chunk["category"],
        "url": chunk["url"],
        "restaurant": chunk["restaurant"] or "",
        "author": chunk["author"] or "",
        "score": chunk["score"] if chunk["score"] is not None else -1,
        "is_question": bool(chunk.get("is_question", False)),
    }


def _keyword_bonus(query, text):
    """Reward chunks whose text overlaps meaningful query terms."""
    tokens = [
        w for w in re.findall(r"[a-z']+", query.lower())
        if w not in QUERY_STOPWORDS and len(w) > 2
    ]
    if not tokens:
        return 0.0
    lower = text.lower()
    hits = sum(1 for tok in tokens if tok in lower)
    return KEYWORD_BONUS * (hits / len(tokens))


def _detect_categories(query):
    """Return direct keyword matches and secondary related categories."""
    q = query.lower()
    direct, also = [], []
    for cat, triggers in CATEGORY_TRIGGERS:
        if any(t in q for t in triggers):
            direct.append(cat)
            also.extend(CATEGORY_ALSO.get(cat, ()))
    def _dedupe(items):
        seen, out = set(), []
        for cat in items:
            if cat not in seen:
                seen.add(cat)
                out.append(cat)
        return out
    direct = _dedupe(direct)
    also = [c for c in _dedupe(also) if c not in set(direct)]
    return direct, also


def _build_where(*, exclude_questions=True, categories=None):
    """Build a ChromaDB metadata filter."""
    clauses = []
    if exclude_questions:
        clauses.append({"is_question": False})
    if categories:
        if len(categories) == 1:
            clauses.append({"category": categories[0]})
        else:
            clauses.append({"category": {"$in": categories}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _query_collection(collection, query_embedding, n_results, where):
    """Run a ChromaDB query and return formatted result dicts keyed by id."""
    kwargs = {
        "query_embeddings": query_embedding,
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where is not None:
        kwargs["where"] = where
    results = collection.query(**kwargs)
    output = {}
    for chunk_id, text, meta, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output[chunk_id] = {
            "id": chunk_id,
            "text": text,
            "source": meta["source"],
            "type": meta["type"],
            "category": meta["category"],
            "url": meta["url"],
            "restaurant": meta["restaurant"] or None,
            "distance": distance,
        }
    return output


def _rerank(candidates, categories, k, *, category_only=False, query=""):
    """Prefer category-matched chunks with restaurants; sort by adjusted distance."""
    cat_set = set(categories)
    scored = []
    for item in candidates.values():
        if category_only and cat_set and item["category"] not in cat_set:
            continue
        adj = item["distance"]
        if cat_set and item["category"] in cat_set:
            adj -= CATEGORY_MATCH_BONUS
        if item["restaurant"]:
            adj -= RESTAURANT_BONUS
        if query:
            adj -= _keyword_bonus(query, item["text"])
        scored.append((adj, item))
    scored.sort(key=lambda x: x[0])
    return [item for _, item in scored[:k]]


def embed_and_store(chunks_path=CHUNKS_PATH, reset=False):
    """Embed all chunks and store them in ChromaDB. Returns number of vectors stored."""
    chunks = load_chunks(chunks_path)
    if not chunks:
        print("No chunks to embed.")
        return 0

    client = _get_client()
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except (ValueError, chromadb.errors.NotFoundError):
            pass

    collection = _get_collection()
    model = _get_model()

    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=BATCH_SIZE)

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=[_clean_metadata(c) for c in chunks],
    )

    print(f"Stored {len(chunks)} vectors -> {CHROMA_DIR / COLLECTION_NAME}")
    print(f"  model: {MODEL_NAME} ({embeddings.shape[1]}-dim)")
    print(f"  collection: {COLLECTION_NAME}")
    return len(chunks)


def retrieve(query, k=TOP_K, exclude_questions=True, use_category=True):
    """Return the top-k most similar chunks for a query string.

    When category keywords are detected, searches direct matches first (e.g.
    family, budget), then related categories (e.g. neighborhood, international),
    then backfills from the general pool only if still short.
    """
    model = _get_model()
    collection = _get_collection()
    query_embedding = model.encode([query]).tolist()

    base_where = _build_where(exclude_questions=exclude_questions)

    if use_category:
        direct, also = _detect_categories(query)
        tiered = direct + also
        if tiered:
            ranked = []
            seen = set()
            for cat in tiered:
                if len(ranked) >= k:
                    break
                cat_where = _build_where(exclude_questions=exclude_questions, categories=[cat])
                n_fetch = min(k * CANDIDATE_MULTIPLIER, 100)
                hits = _query_collection(collection, query_embedding, n_fetch, cat_where)
                batch = _rerank(hits, [cat], k - len(ranked), category_only=True, query=query)
                for item in batch:
                    if item["id"] not in seen:
                        seen.add(item["id"])
                        ranked.append(item)

            if len(ranked) < k:
                n_general = k * CANDIDATE_MULTIPLIER
                general = _query_collection(collection, query_embedding, n_general, base_where)
                pool = {item["id"]: item for item in ranked}
                pool.update(general)
                ranked = _rerank(pool, tiered, k, query=query)
            return ranked

    n_general = k * CANDIDATE_MULTIPLIER
    candidates = _query_collection(collection, query_embedding, n_general, base_where)
    return _rerank(candidates, [], k, query=query)


def _print_results(query, results, categories=None):
    """Print retrieval results for manual inspection."""
    print(f'\nQuery: "{query}"')
    if categories:
        print(f"Categories detected: {', '.join(categories)}")
    print(f"Results: {len(results)}\n")
    for i, r in enumerate(results, 1):
        preview = r["text"].replace("\n", " ")[:200]
        restaurant = r["restaurant"] or "—"
        print(f"  [{i}] id={r['id']}  distance={r['distance']:.4f}  category={r['category']}")
        print(f"      source: {r['source']}")
        print(f"      restaurant: {restaurant}")
        print(f"      {preview}...")
        print()


def main():
    parser = argparse.ArgumentParser(description="Embed chunks and retrieve by similarity.")
    sub = parser.add_subparsers(dest="command", required=True)

    store_p = sub.add_parser("store", help="Embed chunks and store in ChromaDB")
    store_p.add_argument(
        "--reset", action="store_true",
        help="Delete existing collection before storing",
    )

    query_p = sub.add_parser("query", help="Retrieve top-k chunks for a query")
    query_p.add_argument("text", help="Query string")
    query_p.add_argument("-k", type=int, default=TOP_K, help=f"Number of results (default {TOP_K})")
    query_p.add_argument(
        "--include-questions", action="store_true",
        help="Include OP question chunks in results",
    )

    query_p.add_argument(
        "--no-category", action="store_true",
        help="Disable category-aware retrieval (pure semantic search)",
    )

    args = parser.parse_args()

    if args.command == "store":
        embed_and_store(reset=args.reset)
        return 0

    if args.command == "query":
        direct, also = _detect_categories(args.text) if not args.no_category else ([], [])
        categories = direct + also if not args.no_category else None
        results = retrieve(
            args.text,
            k=args.k,
            exclude_questions=not args.include_questions,
            use_category=not args.no_category,
        )
        _print_results(args.text, results, categories=categories or None)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
