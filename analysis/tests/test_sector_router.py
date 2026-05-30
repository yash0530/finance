"""
Tests for sector_router.classify and analyzer registry.
"""
import pytest

import db
import sector_router


@pytest.fixture(autouse=True)
def clean_sector_cache():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM sector_classification_cache")
        conn.commit()
    finally:
        conn.close()
    yield


def test_classify_semiconductor_to_semis():
    cls = sector_router.classify(
        "NVDA",
        fundamentals_data={"sector": "Technology", "industry": "Semiconductors"},
    )
    assert cls["sector_key"] == "semis"
    assert cls["method"] == "rule"
    assert cls["manual_override"] is False


def test_classify_bank_to_banks():
    cls = sector_router.classify(
        "JPM",
        fundamentals_data={"sector": "Financial Services", "industry": "Banks—Diversified"},
    )
    assert cls["sector_key"] == "banks"


def test_classify_software_to_saas():
    cls = sector_router.classify(
        "CRM",
        fundamentals_data={"sector": "Technology", "industry": "Software—Application"},
    )
    assert cls["sector_key"] == "saas"


def test_classify_reit():
    cls = sector_router.classify(
        "O",
        fundamentals_data={"sector": "Real Estate", "industry": "REIT—Retail"},
    )
    assert cls["sector_key"] == "reits"


def test_classify_biotech():
    cls = sector_router.classify(
        "MRNA",
        fundamentals_data={"sector": "Healthcare", "industry": "Biotechnology"},
    )
    assert cls["sector_key"] == "biotech"


def test_classify_energy():
    cls = sector_router.classify(
        "XOM",
        fundamentals_data={"sector": "Energy", "industry": "Oil & Gas Integrated"},
    )
    assert cls["sector_key"] == "energy"


def test_classify_consumer():
    cls = sector_router.classify(
        "MCD",
        fundamentals_data={"sector": "Consumer Cyclical", "industry": "Restaurants"},
    )
    assert cls["sector_key"] == "consumer"


def test_classify_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(
        "llm_service.classify_sector_with_llm",
        lambda *a, **kw: {"sector_key": "default", "confidence": "low"},
    )
    cls = sector_router.classify(
        "ZZZZ",
        fundamentals_data={"sector": "Utilities", "industry": "Diversified Utilities"},
    )
    assert cls["sector_key"] == "default"
    assert cls["confidence"] == "low"


def test_classify_caches_to_db():
    sector_router.classify(
        "NVDA",
        fundamentals_data={"sector": "Technology", "industry": "Semiconductors"},
    )
    cached = db.get_sector_classification("NVDA")
    assert cached is not None
    assert cached["sector_key"] == "semis"


def test_classify_cache_hit_on_second_call():
    sector_router.classify(
        "NVDA",
        fundamentals_data={"sector": "Technology", "industry": "Semiconductors"},
    )
    second = sector_router.classify("NVDA")  # no fundamentals provided this time
    assert second["sector_key"] == "semis"
    assert second["method"] == "cache"


def test_manual_classify_pins_classification():
    sector_router.manual_classify("XYZ", "saas", gics_industry="Software")
    result = sector_router.classify(
        "XYZ",
        fundamentals_data={"sector": "Energy", "industry": "Oil & Gas"},  # would normally route to energy
    )
    # Manual override wins
    assert result["sector_key"] == "saas"
    assert result["manual_override"] is True
    assert result["method"] == "cache"


def test_manual_classify_rejects_unknown_sector():
    with pytest.raises(ValueError):
        sector_router.manual_classify("XYZ", "nonexistent_sector")


def test_get_analyzer_returns_correct_class():
    ana = sector_router.get_analyzer("semis")
    assert ana.sector_key == "semis"
    assert callable(getattr(ana, "required_tools", None))
    assert callable(getattr(ana, "peer_cohort", None))


def test_get_analyzer_unknown_falls_back_to_default():
    ana = sector_router.get_analyzer("does_not_exist")
    assert ana.sector_key == "default"


def test_all_analyzers_have_required_methods():
    """Every analyzer must respond to the 4 interface methods without crashing."""
    for key in sector_router.available_sectors():
        ana = sector_router.get_analyzer(key)
        # Required interface
        assert isinstance(ana.required_tools(), list)
        kpis = ana.kpi_template()
        assert isinstance(kpis, dict)
        peers = ana.peer_cohort("NVDA")
        assert isinstance(peers, list)
        prefix = ana.prompt_prefix()
        assert isinstance(prefix, str)


def test_available_sectors_includes_default():
    sectors = sector_router.available_sectors()
    assert "default" in sectors
    assert len(sectors) >= 7


# ============================================================================
# C3 — LLM fallback
# ============================================================================

def test_llm_fallback_used_when_rules_dont_match(monkeypatch):
    def fake_classify(ticker, sector_str, industry_str, valid_keys):
        assert "semis" in valid_keys  # caller passes the real list
        return {"sector_key": "semis", "confidence": "medium", "reasoning": "fab-related"}

    monkeypatch.setattr("llm_service.classify_sector_with_llm", fake_classify)

    cls = sector_router.classify(
        "ZZZX",
        fundamentals_data={"sector": "Industrials", "industry": "Specialty Industrial Machinery"},
    )
    assert cls["sector_key"] == "semis"
    assert cls["method"] == "llm"
    assert cls["confidence"] == "medium"


def test_llm_fallback_falls_through_to_default_on_failure(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("LLM down")

    monkeypatch.setattr("llm_service.classify_sector_with_llm", boom)

    cls = sector_router.classify(
        "ZZZY",
        fundamentals_data={"sector": "Utilities", "industry": "Diversified Utilities"},
    )
    assert cls["sector_key"] == "default"
    assert cls["method"] == "default"


def test_llm_fallback_skipped_when_rules_match(monkeypatch):
    """Rule match should win — LLM must not be called."""
    call_count = {"n": 0}

    def should_not_run(*a, **kw):
        call_count["n"] += 1
        return {"sector_key": "biotech", "confidence": "high"}

    monkeypatch.setattr("llm_service.classify_sector_with_llm", should_not_run)

    cls = sector_router.classify(
        "NVDA",
        fundamentals_data={"sector": "Technology", "industry": "Semiconductors"},
    )
    assert cls["sector_key"] == "semis"
    assert cls["method"] == "rule"
    assert call_count["n"] == 0


def test_llm_fallback_default_response_treated_as_no_match(monkeypatch):
    """LLM returning 'default' should NOT be saved with method='llm' — fall through."""
    monkeypatch.setattr(
        "llm_service.classify_sector_with_llm",
        lambda *a, **kw: {"sector_key": "default", "confidence": "low"},
    )

    cls = sector_router.classify(
        "ZZZZ",
        fundamentals_data={"sector": "Conglomerate", "industry": "Diversified"},
    )
    assert cls["sector_key"] == "default"
    assert cls["method"] == "default"


def test_llm_result_is_cached(monkeypatch):
    monkeypatch.setattr(
        "llm_service.classify_sector_with_llm",
        lambda *a, **kw: {"sector_key": "consumer", "confidence": "high"},
    )

    sector_router.classify(
        "ZZZA",
        fundamentals_data={"sector": "Other", "industry": "Mixed"},
    )
    cached = db.get_sector_classification("ZZZA")
    assert cached is not None
    assert cached["sector_key"] == "consumer"
    assert cached["method"] == "llm"


def test_classify_sector_with_llm_helper_clamps_bad_key(monkeypatch):
    """The llm_service.classify_sector_with_llm helper should clamp an invalid
    sector_key to 'default' rather than letting it propagate."""
    from llm_service import classify_sector_with_llm

    class _StubProvider:
        def complete_json(self, system, user, model):
            return {"sector_key": "made_up_bucket", "confidence": "high", "reasoning": "bad"}

    monkeypatch.setattr("llm_service._get_provider_and_model", lambda t, role="unknown": (_StubProvider(), "fake-model"))

    out = classify_sector_with_llm("NVDA", "Tech", "Semis", ["semis", "saas", "default"])
    assert out["sector_key"] == "default"
    assert out["confidence"] == "low"
    assert "error" in out


def test_classify_sector_with_llm_helper_handles_non_dict(monkeypatch):
    from llm_service import classify_sector_with_llm

    class _StubProvider:
        def complete_json(self, system, user, model):
            return "not a dict"

    monkeypatch.setattr("llm_service._get_provider_and_model", lambda t, role="unknown": (_StubProvider(), "fake-model"))

    out = classify_sector_with_llm("NVDA", "Tech", "Semis", ["semis"])
    assert out["sector_key"] == "default"
    assert out["confidence"] == "low"
