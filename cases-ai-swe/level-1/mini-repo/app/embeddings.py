# embeddings , offline deterministic embedder. token-hash -> fixed dim, L2-normalized. No API key.
import hashlib
import math

DIM = 64


def _tokens(text):
    clean = "".join(c.lower() if c.isalnum() else " " for c in (text or ""))
    return [t for t in clean.split() if t]


def embed(text):
    v = [0.0] * DIM
    for tok in _tokens(text):
        idx = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16) % DIM
        v[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]
