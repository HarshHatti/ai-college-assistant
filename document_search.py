import math
from pathlib import Path

import ollama
from pypdf import PdfReader

EMBED_MODEL = "embeddinggemma"
DOCS_FOLDER = Path("documents")

# Each item: {"source": file name, "page": number, "text": chunk, "embedding": [...]}
INDEX = []


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _split_text(text, size=800, overlap=100):
    """Cut text into chunks of about `size` characters, overlapping a little."""
    chunks, start = [], 0
    while start < len(text):
        chunk = text[start:start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks


def _embed(texts):
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    return response["embeddings"]


def index_pdf(path):
    """Read a PDF, chunk it, embed the chunks and add them to the index."""
    path = Path(path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {path}"}

    try:
        reader = PdfReader(str(path))
    except Exception as e:
        return {"success": False, "error": f"Could not open PDF: {e}"}

    # remove old chunks of this file so it is not indexed twice
    INDEX[:] = [c for c in INDEX if c["source"] != path.name]

    new_chunks = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for chunk in _split_text(text):
            new_chunks.append({"source": path.name, "page": page_number, "text": chunk})

    if not new_chunks:
        return {"success": False, "error": "No text found. The PDF may be scanned (images only)."}

    try:
        embeddings = _embed([c["text"] for c in new_chunks])
    except Exception as e:
        return {"success": False, "error": f"Embedding failed: {e}"}

    for chunk, emb in zip(new_chunks, embeddings):
        chunk["embedding"] = emb
    INDEX.extend(new_chunks)
    return {"success": True, "file": path.name, "chunks": len(new_chunks)}


def search_documents(question, top_k=3):
    """Find the chunks most similar to the question."""
    if not INDEX:
        return {"success": False, "error": "No documents loaded yet. Upload a PDF first."}
    if not (question or "").strip():
        return {"success": False, "error": "Question cannot be empty."}

    try:
        q_emb = _embed([question])[0]
    except Exception as e:
        return {"success": False, "error": f"Embedding failed: {e}"}

    scored = sorted(INDEX, key=lambda c: _cosine(q_emb, c["embedding"]), reverse=True)
    results = [
        {"source": c["source"], "page": c["page"], "text": c["text"]}
        for c in scored[:top_k]
    ]
    return {"success": True, "results": results}


if __name__ == "__main__":
    pdfs = list(DOCS_FOLDER.glob("*.pdf"))
    if not pdfs:
        print("Put a PDF in the documents/ folder first.")
    else:
        print(index_pdf(pdfs[0]))
        out = search_documents("What is this document about?")
        for r in out.get("results", []):
            print(f"\n[{r['source']} p.{r['page']}]\n{r['text'][:300]}")