"""
Tests for the /api/docs endpoints (D1).

Verifies the manifest filter logic and the slug→file whitelist that prevents
path traversal.
"""
from __future__ import annotations

import os

import pytest

import app as _app  # noqa: F401 — imports register routes


@pytest.fixture
def client():
    _app.app.config["TESTING"] = True
    with _app.app.test_client() as c:
        yield c


def test_list_docs_returns_all_present(client):
    res = client.get("/api/docs")
    assert res.status_code == 200
    body = res.get_json()
    assert "docs" in body and isinstance(body["docs"], list)
    slugs = {d["slug"] for d in body["docs"]}
    # All 5 user-facing guides should be present and on disk
    for required in ("getting-started", "how-to-invest", "understanding-outputs",
                     "troubleshooting", "architecture"):
        assert required in slugs, f"Missing slug: {required}"


def test_list_docs_sorted_by_order(client):
    res = client.get("/api/docs")
    body = res.get_json()
    orders = [d["order"] for d in body["docs"]]
    assert orders == sorted(orders), "docs not sorted by order"


def test_get_doc_returns_body_and_toc(client):
    res = client.get("/api/docs/getting-started")
    assert res.status_code == 200
    body = res.get_json()
    assert body["slug"] == "getting-started"
    assert body["title"]
    assert body["category"]
    assert isinstance(body["body"], str) and len(body["body"]) > 100
    assert isinstance(body["toc"], list) and len(body["toc"]) > 0
    # Each TOC entry has the expected shape
    for entry in body["toc"]:
        assert entry["level"] in (2, 3)
        assert entry["text"]
        assert entry["anchor"]


def test_get_doc_unknown_slug_404(client):
    res = client.get("/api/docs/totally-fake-slug")
    assert res.status_code == 404


def test_get_doc_path_traversal_blocked(client):
    """Slugs like ../../etc/passwd must NOT resolve."""
    res = client.get("/api/docs/..%2F..%2Fetc%2Fpasswd")
    assert res.status_code == 404


def test_get_doc_dotfile_blocked(client):
    """Even slugs that exist as files on disk shouldn't resolve unless whitelisted."""
    # The CLAUDE.md file lives in analysis/docs/ but isn't in the manifest
    res = client.get("/api/docs/CLAUDE")
    assert res.status_code == 404


def test_toc_ignores_headings_inside_code_blocks(client):
    """A line like '## Anchor' inside a ``` fence must not show up in the TOC."""
    res = client.get("/api/docs/architecture")
    body = res.get_json()
    # The architecture doc has a fenced tree block; nothing inside it should
    # contain a leading '##' that would survive into the TOC. This is a soft
    # check — we just verify TOC entries don't include any obvious file-tree
    # markers.
    for entry in body["toc"]:
        assert not entry["text"].startswith("|"), f"TOC bled in: {entry}"
