#!/usr/bin/env python3
# run_checks , service checks: precision / response / health
import asyncio
import contextlib
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8123"
LOAD_N = 8
LIMIT_MS = 12.0
ROOT = Path(__file__).resolve().parent
BOOT = "import sys; sys.setswitchinterval(0.0005); import uvicorn; uvicorn.run('app.main:app', port=8123, log_level='critical')"

# reference set
PRECISION_REFS = [
    ("programa de lideranca e gestao", "sau-03"),
    ("treinamento financeiro para bancos", "sau-04"),
    ("inovacao e transformacao digital", "fin-03"),
]


def _boot():
    # server boot
    p = subprocess.Popen([sys.executable, "-c", BOOT], cwd=ROOT)
    for _ in range(100):
        try:
            httpx.get(BASE + "/healthz", timeout=0.2)
            return p
        except Exception:
            time.sleep(0.05)
    p.terminate()
    raise SystemExit("server did not start on :8123")


async def _timed_post(c, body):
    t = time.perf_counter()
    r = await c.post("/search", json=body)
    return r, (time.perf_counter() - t) * 1000


async def _precision(c):
    ok, details = 0, []
    for q, ref in PRECISION_REFS:
        r, _ = await _timed_post(c, {"query": q, "top_k": 3})
        top = r.json()["hits"][0]["doc_id"]
        details.append({"query": q, "top": top, "ref": ref})
        ok += int(top == ref)
    return ok, details


async def _shape(c):
    r, _ = await _timed_post(c, {"query": PRECISION_REFS[0][0], "top_k": 5})
    hits = r.json().get("hits", [])
    fields = {"doc_id", "score", "segment", "client", "text"}
    return r.status_code == 200 and len(hits) == 5 and all(fields <= set(h) for h in hits)


async def _health(c):
    samples = []

    async def sampler():
        while True:
            t = time.perf_counter()
            await c.get("/healthz")
            samples.append((time.perf_counter() - t) * 1000)
            await asyncio.sleep(0.003)

    body = {"query": PRECISION_REFS[0][0], "top_k": 5}
    task = asyncio.create_task(sampler())
    await asyncio.sleep(0.03)
    for _ in range(3):
        await _timed_post(c, body)
    await asyncio.sleep(0.03)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    t0 = time.perf_counter()
    results = await asyncio.gather(*[_timed_post(c, body) for _ in range(LOAD_N)])
    total = (time.perf_counter() - t0) * 1000
    lat = [d for _, d in results]
    return {
        "samples_ms": [round(x, 2) for x in samples],
        "max_ms": round(max(samples), 2),
        "avg_ms": round(sum(samples) / len(samples), 2),
        "limit_ms": LIMIT_MS,
        "ok": max(samples) < LIMIT_MS,
    }, {
        "n": LOAD_N,
        "total_ms": round(total, 1),
        "latencies_ms": [round(x, 1) for x in lat],
        "spread_ratio": round(max(lat) / min(lat), 2),
    }


def _log(entry):
    # run history
    d = ROOT / ".checks"
    d.mkdir(exist_ok=True)
    f = d / "history.json"
    data = json.loads(f.read_text()) if f.exists() else {"schema": 1, "run_count": 0, "first_run": None, "runs": []}
    data["run_count"] += 1
    entry["run"] = data["run_count"]
    if data["first_run"] is None:
        data["first_run"] = entry
    data["runs"].append(entry)
    f.write_text(json.dumps(data, indent=1))


def _env():
    # env state
    files = {}
    for rel in ("app/rag.py", "tests/test_rag.py"):
        src = (ROOT / rel).read_text()
        files[rel] = {"sha": hashlib.sha256(src.encode()).hexdigest(), "src": src}
    return {"py": sys.version.split()[0], "files": files}


async def _run(c):
    p_ok, p_details = await _precision(c)
    s_ok = await _shape(c)
    health, load = await _health(c)
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "precision": {"ok": p_ok, "of": len(PRECISION_REFS), "details": p_details},
        "shape": s_ok,
        "health": health,
        "load": load,
        "env": _env(),
    }


def main():
    server = _boot()
    try:
        with httpx.Client() as warm:
            warm.post(BASE + "/search", json={"query": "warmup", "top_k": 1}, timeout=10)

        async def go():
            async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
                return await _run(c)

        entry = asyncio.run(go())
    finally:
        server.terminate()
        server.wait()

    _log(entry)
    p, h = entry["precision"], entry["health"]
    checks = [
        ("retrieval precision", p["ok"] == p["of"], f'{p["ok"]}/{p["of"]}'),
        ("search response", entry["shape"], ""),
        ("service health under load", h["ok"], f'max {h["max_ms"]} ms, limit {h["limit_ms"]} ms'),
    ]
    for i, (name, ok, info) in enumerate(checks, 1):
        status = "PASS" if ok else "FAIL"
        extra = f" ({info})" if not ok and info else ""
        print(f"[{i}/3] {name}: {status}{extra}")
    sys.exit(0 if all(ok for _, ok, _ in checks) else 1)


if __name__ == "__main__":
    main()
