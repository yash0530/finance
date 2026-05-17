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


def test_classify_falls_back_to_default():
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
