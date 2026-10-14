# Retrieval design

## Responsiveness

`retrieve()` was declared async but never awaited anything: embedding, scoring,
sorting and `_per_doc_cost()` all ran on the server's event loop. While a search
was running, the loop could not serve `/healthz` or advance streaming responses.
The async entry point now awaits `run_in_executor` with a `ProcessPoolExecutor`,
which runs the entire synchronous retrieval operation in a worker process. Both search and
generation use this entry point. `_per_doc_cost()` remains unchanged and runs
for each eligible document.

One worker bounds CPU concurrency and isolates the search from the event loop's
GIL. The application shuts down the pool at the end of its lifespan. The cost is
process startup, serialization of arguments/results and a separate document cache
in the worker. Searches queue when the worker is busy; this preserves responsiveness
but does not improve algorithmic complexity. For larger workloads, add admission
control and timeouts, then size the worker pool to the CPU and memory budget.

## Metadata filters

Each provided filter uses exact, case-sensitive equality. `None` means no
restriction; an empty string is a literal filter value. When both `segment` and
`client` are present, documents must match both. Filtering happens before scoring
and the per-document cost, then results are sorted and truncated to `top_k`.
Consequently, the endpoint returns the best matches within the requested subset,
possibly fewer than `top_k`, or an empty list. Tests cover the five Financeiro
documents, client-only and combined filters, incompatible and unknown values,
an empty value, and the streaming endpoint.

## Production scale

The current search scans all documents and sorts all eligible scores. At scale,
precompute versioned embeddings during ingestion and use a vector index with
approximate nearest-neighbor search and indexed metadata filtering. Evaluate
recall, ranking quality and latency against a representative query set before
selecting index parameters. A retrieval service can handle batching, caching,
bounded concurrency and incremental index updates; monitor tail latency and
freshness, and enforce any access restrictions within retrieval itself.
