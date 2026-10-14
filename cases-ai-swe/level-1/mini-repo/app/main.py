# main , FastAPI app. /search + /generate/stream (SSE) + /healthz.
import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.models import SearchRequest
from app.rag import retrieve, shutdown_retrieval

@asynccontextmanager
async def lifespan(app):
    try:
        yield
    finally:
        shutdown_retrieval()


app = FastAPI(title="proposal-rag-mini", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/search")
async def search(req: SearchRequest):
    hits = await retrieve(req.query, req.top_k, req.segment, req.client)
    return {"hits": hits}


@app.post("/generate/stream")
async def generate_stream(req: SearchRequest):
    # streaming proposal draft (offline stub, no external API)
    hits = await retrieve(req.query, req.top_k, req.segment, req.client)

    async def gen():
        yield f"event: metadata\ndata: {json.dumps({'used': len(hits)})}\n\n"
        for word in _draft(hits).split():
            yield f"event: chunk\ndata: {json.dumps({'content': word + ' '})}\n\n"
            await asyncio.sleep(0)
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


def _draft(hits):
    client = hits[0]["client"] if hits else "cliente"
    return f"Proposta FGV In Company para {client}. Baseada em {len(hits)} referencias historicas."
