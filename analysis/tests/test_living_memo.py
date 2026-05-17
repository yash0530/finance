"""
Tests for the Living Memo module.
"""
import pytest

import db
import living_memo


@pytest.fixture(autouse=True)
def clean_memo_tables():
    conn = db.get_connection()
    try:
        for t in ("living_memo", "living_memo_versions"):
            conn.execute(f"DELETE FROM {t}")
        conn.commit()
    finally:
        conn.close()
    yield


def test_empty_memo_has_all_sections():
    memo = living_memo.empty_memo()
    for sec in living_memo.MEMO_SECTIONS:
        assert sec in memo
        # Each section is a dict (risk_register and past_verdicts may use structured: list)
        assert isinstance(memo[sec], dict)
        assert "content_md" in memo[sec]
        assert "confidence" in memo[sec]


def test_save_load_roundtrip():
    content = living_memo.empty_memo()
    content["identity"]["content_md"] = "GPU + AI compute leader"
    content["moat"]["content_md"] = "CUDA ecosystem, scale, ML stack"
    living_memo.save("NVDA", content, delta_summary="initial")

    loaded = living_memo.load("NVDA")
    assert loaded is not None
    assert loaded["current_version"] == 1
    assert loaded["content_json"]["identity"]["content_md"].startswith("GPU")


def test_load_or_empty_returns_skeleton_when_absent():
    memo = living_memo.load_or_empty("NEWTKR")
    assert memo is not None
    # Either has the empty skeleton sections directly, or wraps under content_json
    if "content_json" in memo:
        sections = memo["content_json"]
    else:
        sections = memo
    for s in living_memo.MEMO_SECTIONS:
        assert s in sections


def test_version_increments():
    living_memo.save("NVDA", living_memo.empty_memo(), delta_summary="v1")
    living_memo.save("NVDA", living_memo.empty_memo(), delta_summary="v2")
    living_memo.save("NVDA", living_memo.empty_memo(), delta_summary="v3")
    memo = living_memo.load("NVDA")
    assert memo["current_version"] == 3
    versions = living_memo.history("NVDA")
    assert len(versions) == 3
    assert versions[0]["version"] == 3
    assert versions[-1]["version"] == 1


def test_render_produces_markdown():
    content = living_memo.empty_memo()
    content["identity"]["content_md"] = "GPU maker"
    content["moat"]["content_md"] = "CUDA"
    md = living_memo.render(content)
    assert isinstance(md, str)
    assert "GPU maker" in md
    assert "CUDA" in md


def test_get_open_questions_returns_list():
    content = living_memo.empty_memo()
    content["open_questions"]["content_md"] = "- Will gross margin hold above 70%?\n- Is hyperscaler capex peaking?"
    qs = living_memo.get_open_questions({"content_json": content})
    assert isinstance(qs, list)
    assert len(qs) >= 1


def test_get_version_returns_specific_historical():
    c1 = living_memo.empty_memo()
    c1["identity"]["content_md"] = "v1 identity"
    living_memo.save("NVDA", c1, delta_summary="initial")

    c2 = living_memo.empty_memo()
    c2["identity"]["content_md"] = "v2 identity"
    living_memo.save("NVDA", c2, delta_summary="updated")

    v1 = living_memo.get_version("NVDA", 1)
    assert v1 is not None
    assert "v1 identity" in v1["content_json"]["identity"]["content_md"]

    missing = living_memo.get_version("NVDA", 99)
    assert missing is None


def test_memo_read_tool_when_absent():
    from tools import get_tool
    tool = get_tool("memo_read")
    assert tool is not None
    result = tool.execute(ticker="NEVER_RESEARCHED")
    assert result.is_ok()
    assert result.data["exists"] is False


def test_memo_read_tool_when_present():
    content = living_memo.empty_memo()
    content["identity"]["content_md"] = "Test biz"
    living_memo.save("NVDA", content)

    from tools import get_tool
    tool = get_tool("memo_read")
    result = tool.execute(ticker="NVDA")
    assert result.is_ok()
    assert result.data["exists"] is True
    assert result.data["version"] == 1
    assert "identity" in result.data["sections"]
