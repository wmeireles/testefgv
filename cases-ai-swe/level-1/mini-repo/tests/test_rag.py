# tests , run with: pytest -q
from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


def test_search_returns_topk():
    # passing baseline , the harness works
    r = client.post("/search", json={"query": "programa de lideranca e gestao", "top_k": 3})
    assert r.status_code == 200
    hits = r.json()["hits"]
    assert len(hits) == 3
    assert all("score" in h for h in hits)


def test_metadata_filter():
    # 5 Financeiro docs: segment="Financeiro" + top_k=5 must return 5 hits, all Financeiro.
    r = client.post(
        "/search",
        json={"query": "programa de lideranca e gestao", "top_k": 5, "segment": "Financeiro"},
    )
    assert r.status_code == 200
    hits = r.json()["hits"]
    assert len(hits) == 5
    assert all(h["segment"] == "Financeiro" for h in hits)
    assert {h["doc_id"] for h in hits} == {f"fin-{i:02d}" for i in range(1, 6)}


@pytest.mark.parametrize(
    "filters, expected_ids",
    [
        ({"client": "Banco Aurora"}, {"fin-01", "fin-05"}),
        ({"segment": "Financeiro", "client": "Banco Aurora"}, {"fin-01", "fin-05"}),
        ({"segment": "Saude", "client": "Banco Aurora"}, set()),
        ({"segment": "Inexistente"}, set()),
        ({"client": "Inexistente"}, set()),
        ({"segment": ""}, set()),
    ],
)
def test_metadata_filter_combinations(filters, expected_ids):
    r = client.post(
        "/search",
        json={"query": "programa de lideranca e gestao", "top_k": 5, **filters},
    )
    assert r.status_code == 200
    hits = r.json()["hits"]
    assert {h["doc_id"] for h in hits} == expected_ids
    assert all(all(h[key] == value for key, value in filters.items()) for h in hits)


def test_stream_uses_metadata_filter():
    r = client.post(
        "/generate/stream",
        json={"query": "lideranca", "segment": "Financeiro", "client": "Banco Aurora"},
    )
    assert r.status_code == 200
    assert 'event: metadata\ndata: {"used": 2}' in r.text
    assert "event: done" in r.text
