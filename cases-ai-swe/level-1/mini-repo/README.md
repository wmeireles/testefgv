# proposal-rag-mini , Level 1 take-home

A trimmed RAG service behind the FGV proposal copilot. It runs fully offline (no API keys, deterministic embedder). Budget about 2 to 3 hours. Use any AI tools you want, we do.

## Setup
```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pytest -q                       # one test passes, one is yours to complete (Task 2)
python run_checks.py            # service checks, all must pass
uvicorn app.main:app --reload   # then POST /search, /generate/stream, GET /healthz
```
Example:
```
curl -s localhost:8000/search -H 'content-type: application/json' \
  -d '{"query":"programa de lideranca","top_k":3}'
```

## Your tasks
1. **Fix the performance problem.** Under concurrent load the service stops responding while searches run, and `run_checks.py` fails the health check. Fix it so all checks pass. Note: `_per_doc_cost()` stands in for real per-chunk cost, keep it, do not just delete it.
2. **Implement the metadata filter.** `retrieve()` accepts `segment` and `client` but ignores them. Implement the filter, then complete `test_metadata_filter` in `tests/test_rag.py` so it passes.

## Also deliver: `DESIGN.md` (half page)
- The performance problem: what it was, how you fixed it, the trade-off.
- The metadata filter: your approach and why.
- This search is O(n) brute force in Python. How would you take it to production scale? (one short paragraph)

## What we look at
Does it run, do tests and checks pass, is the code clean, is the design note sharp. We talk through it live afterward.
