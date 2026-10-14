# rag , retrieval over document chunks (Tasks 1 and 2, see README)
import asyncio
from concurrent.futures import ProcessPoolExecutor

from app.embeddings import embed
from app.store import documents

_pool = None


def shutdown_retrieval():
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=True)
        _pool = None


def _cosine(a, b):
    return sum(x * y for x, y in zip(a, b))


def _per_doc_cost():
    # per-chunk cost stand-in , keep
    x = 0.0
    for i in range(60000):
        x += i * 0.5
    return x


async def retrieve(query, top_k=5, segment=None, client=None):
    global _pool
    # A separate process avoids contention for the event loop's Python GIL.
    if _pool is None:
        _pool = ProcessPoolExecutor(max_workers=1)
    return await asyncio.get_running_loop().run_in_executor(
        _pool, _retrieve, query, top_k, segment, client
    )


def _retrieve(query, top_k, segment, client):
    q = embed(query)
    scored = []
    for d in documents():
        if segment is not None and d["segment"] != segment:
            continue
        if client is not None and d["client"] != client:
            continue
        score = _cosine(q, d["embedding"])
        _per_doc_cost()
        scored.append((score, d))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [_hit(s, d) for s, d in scored[:top_k]]


def _hit(score, d):
    return {
        "doc_id": d["id"], "score": round(score, 4), "segment": d["segment"],
        "client": d["client"], "text": d["text"],
    }
