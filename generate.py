"""Grounded answer generation via Groq LLM over retrieved chunks.

Pipeline stage (see planning.md > Architecture):
  1. retrieve(query) from retrieval.py → top-k chunks
  2. Format chunks as numbered documents for the LLM prompt
  3. Call Groq llama-3.3-70b-versatile with strict grounding instructions
  4. Return answer + programmatically built source list

Usage:
    python -c "from generate import ask; print(ask('Where can I get crab cakes?'))"
"""

import os
import sys

from dotenv import load_dotenv
from groq import Groq

from retrieval import retrieve

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
DEFAULT_K = 5
INSUFFICIENT_INFO = "I don't have enough information on that."

SYSTEM_PROMPT = (
    "You are a Baltimore restaurant guide assistant. "
    "You MUST answer using ONLY the information in the user's provided documents. "
    "You MUST NOT use any outside knowledge. "
    "If the documents name restaurants or describe dining options relevant to the question, "
    "you MUST recommend them using details from the documents. "
    f"Only if the documents contain NO relevant information, "
    f'respond with exactly: "{INSUFFICIENT_INFO}" '
    "Do not invent restaurant names, addresses, or details not present in the documents. "
    "Do not include source citations in your answer — sources are handled separately. "
    "Be concise and helpful."
)

_client = None


def _get_client():
    """Lazy-load Groq client; fail fast if API key is missing."""
    global _client
    if _client is None:
        if not os.getenv("GROQ_API_KEY"):
            raise EnvironmentError(
                "GROQ_API_KEY not set — copy .env.example to .env and add your key."
            )
        _client = Groq()
    return _client


def format_context(chunks):
    """Format retrieved chunks as numbered document blocks for the LLM."""
    blocks = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[Document {i}] Source: {chunk['source']}"
        if chunk.get("restaurant"):
            header += f" | Restaurant: {chunk['restaurant']}"
        blocks.append(f"{header}\n{chunk['text']}")
    return "\n\n".join(blocks)


def build_messages(query, chunks):
    """Return system + user messages for the Groq chat API."""
    context = format_context(chunks)
    user_content = f"Documents:\n{context}\n\nQuestion: {query}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_sources(chunks):
    """Build deduplicated source attribution strings from chunk metadata."""
    seen = {}
    for chunk in chunks:
        key = (chunk["source"], chunk["url"])
        if key not in seen:
            seen[key] = {
                "source": chunk["source"],
                "url": chunk["url"],
                "type": chunk["type"],
                "restaurants": set(),
            }
        if chunk.get("restaurant"):
            for name in chunk["restaurant"].split(","):
                name = name.strip()
                if name:
                    seen[key]["restaurants"].add(name)

    lines = []
    for entry in seen.values():
        type_label = "Reddit" if entry["type"] == "reddit" else "Article"
        line = f"{entry['source']} ({type_label}) — {entry['url']}"
        if entry["restaurants"]:
            names = ", ".join(sorted(entry["restaurants"]))
            line += f" [Restaurants: {names}]"
        lines.append(line)
    return lines


def ask(query, k=DEFAULT_K):
    """Retrieve chunks, generate a grounded answer, and return sources programmatically."""
    chunks = retrieve(query, k=k)

    if not chunks:
        return {
            "answer": INSUFFICIENT_INFO,
            "sources": [],
            "chunks": [],
        }

    sources = build_sources(chunks)
    messages = build_messages(query, chunks)
    client = _get_client()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
    )
    answer = response.choices[0].message.content.strip()

    return {
        "answer": answer,
        "sources": sources,
        "chunks": chunks,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ask a grounded question.")
    parser.add_argument("question", help="Question to ask")
    parser.add_argument("-k", type=int, default=DEFAULT_K, help="Number of chunks to retrieve")
    args = parser.parse_args()

    result = ask(args.question, k=args.k)
    print("Answer:")
    print(result["answer"])
    print("\nRetrieved from:")
    for src in result["sources"]:
        print(f"  • {src}")
