"""
Tests for BoardCompositionCollector — proxy HTML parsing, caching, and
end-to-end scoring integration with BoardCompositionAnalyzer.
"""

import sys
import json
import tempfile
from pathlib import Path
from decimal import Decimal

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from app.pipelines.board_collector import BoardCompositionCollector
from scoring.board_analyzer import BoardCompositionAnalyzer, BoardMember


# ── HTML fixtures ────────────────────────────────────────────────────

SAMPLE_PROXY_HTML = """
<html>
<body>
<h2>Proposal 1 — Election of Directors</h2>
<div>
    <table>
        <tr>
            <td>Dr. Jane Smith</td>
            <td>Independent Director. Chief Technology Officer of Acme Corp.
                Expertise in artificial intelligence and machine learning.
                Member of the Technology Committee and Audit Committee.
                Appointed since 2018.</td>
        </tr>
        <tr>
            <td>John Doe</td>
            <td>Independent Director. Former President and CEO.
                Member of the Compensation Committee and Risk Committee.
                Serving since 2015.</td>
        </tr>
        <tr>
            <td>Alice Johnson</td>
            <td>Chief Data Officer. Leads data science and analytics initiatives.
                Member of the Audit Committee. Joined 2020.</td>
        </tr>
        <tr>
            <td>Bob Williams</td>
            <td>Director. Background in finance and operations.
                Member of the Finance Committee. Since 2019.</td>
        </tr>
        <tr>
            <td>Carol Davis</td>
            <td>Independent Director. Expertise in cybersecurity and digital strategy.
                Member of the Risk Committee. Appointed 2021.</td>
        </tr>
    </table>
</div>

<h3>Committees of the Board</h3>
<p>The board has the following committees: audit committee, compensation committee,
technology committee, risk management committee, and finance committee.</p>

<h3>Strategy</h3>
<p>Our company is investing in artificial intelligence to drive innovation.
We are also leveraging machine learning across our operations.</p>
</body>
</html>
"""

MINIMAL_PROXY_HTML = """
<html><body>
<h2>Board of Directors</h2>
<div>
    <p><b>Sarah Connor</b></p>
    <p>Independent Director. Since 2022.</p>
    <p><b>James Kirk</b></p>
    <p>Director. Chairman of the board.</p>
</div>
</body></html>
"""

EMPTY_PROXY_HTML = """
<html><body><p>No relevant board information.</p></body></html>
"""


# ── Collector instance (with temp dir) ────────────────────────────────

def _make_collector(tmp_dir=None):
    d = tmp_dir or tempfile.mkdtemp()
    return BoardCompositionCollector(data_dir=d)


# ── HTML Parsing Tests ────────────────────────────────────────────────

def test_parse_proxy_extracts_members():
    """Members are extracted from a typical proxy table."""
    collector = _make_collector()
    data = collector.parse_proxy_html(SAMPLE_PROXY_HTML)

    assert "members" in data
    assert len(data["members"]) >= 3, f"Expected >=3 members, got {len(data['members'])}"
    names = [m["name"] for m in data["members"]]
    assert "Dr. Jane Smith" in names
    print("PASS test_parse_proxy_extracts_members")


def test_parse_proxy_extracts_committees():
    """Committee names are extracted from narrative text."""
    collector = _make_collector()
    data = collector.parse_proxy_html(SAMPLE_PROXY_HTML)

    assert "committees" in data
    committee_lower = [c.lower() for c in data["committees"]]
    assert any("technology" in c for c in committee_lower), f"No technology committee found in {data['committees']}"
    assert any("audit" in c for c in committee_lower)
    print("PASS test_parse_proxy_extracts_committees")


def test_parse_proxy_extracts_strategy_text():
    """Strategy passages mentioning AI/ML are extracted."""
    collector = _make_collector()
    data = collector.parse_proxy_html(SAMPLE_PROXY_HTML)

    assert "strategy_text" in data
    assert "artificial intelligence" in data["strategy_text"]
    print("PASS test_parse_proxy_extracts_strategy_text")


def test_parse_proxy_independent_detection():
    """Independent directors are flagged correctly."""
    collector = _make_collector()
    data = collector.parse_proxy_html(SAMPLE_PROXY_HTML)

    independent_members = [m for m in data["members"] if m["is_independent"]]
    assert len(independent_members) >= 2, f"Expected >=2 independent, got {len(independent_members)}"
    print("PASS test_parse_proxy_independent_detection")


def test_parse_proxy_tenure_extraction():
    """Tenure years are extracted from 'since YYYY' patterns."""
    collector = _make_collector()
    data = collector.parse_proxy_html(SAMPLE_PROXY_HTML)

    members_with_tenure = [m for m in data["members"] if m["tenure_years"] > 0]
    assert len(members_with_tenure) >= 1, "Expected at least one member with tenure extracted"
    print("PASS test_parse_proxy_tenure_extraction")


def test_parse_proxy_member_committees():
    """Per-member committee memberships are extracted."""
    collector = _make_collector()
    data = collector.parse_proxy_html(SAMPLE_PROXY_HTML)

    jane = next((m for m in data["members"] if "Jane" in m["name"]), None)
    assert jane is not None, "Dr. Jane Smith not found"
    committee_lower = [c.lower() for c in jane["committees"]]
    assert any("technology" in c for c in committee_lower), f"Expected technology committee in {jane['committees']}"
    print("PASS test_parse_proxy_member_committees")


def test_parse_empty_proxy():
    """Empty/irrelevant HTML returns empty data without errors."""
    collector = _make_collector()
    data = collector.parse_proxy_html(EMPTY_PROXY_HTML)

    assert data["members"] == []
    assert data["strategy_text"] == ""
    print("PASS test_parse_empty_proxy")


def test_parse_minimal_proxy_bold_fallback():
    """Bold-name fallback strategy finds directors when no table exists."""
    collector = _make_collector()
    data = collector.parse_proxy_html(MINIMAL_PROXY_HTML)

    names = [m["name"] for m in data["members"]]
    assert "Sarah Connor" in names or "James Kirk" in names, f"Expected bold-name extraction, got {names}"
    print("PASS test_parse_minimal_proxy_bold_fallback")


def test_parse_returns_all_expected_keys():
    """Parsed data always contains members, committees, strategy_text."""
    collector = _make_collector()
    for html in [SAMPLE_PROXY_HTML, MINIMAL_PROXY_HTML, EMPTY_PROXY_HTML]:
        data = collector.parse_proxy_html(html)
        assert "members" in data
        assert "committees" in data
        assert "strategy_text" in data
        for m in data["members"]:
            assert "name" in m
            assert "title" in m
            assert "bio" in m
            assert "is_independent" in m
            assert "committees" in m
            assert "tenure_years" in m
    print("PASS test_parse_returns_all_expected_keys")


# ── Cache Tests ───────────────────────────────────────────────────────

def test_cache_round_trip():
    """Data saved to cache can be loaded back identically."""
    tmp = tempfile.mkdtemp()
    collector = BoardCompositionCollector(data_dir=tmp)

    original = {
        "members": [
            {
                "name": "Test Person",
                "title": "Director",
                "bio": "Some bio",
                "is_independent": True,
                "committees": ["Audit Committee"],
                "tenure_years": 5.0,
            }
        ],
        "committees": ["Audit Committee", "Technology Committee"],
        "strategy_text": "artificial intelligence is key",
    }

    collector._cache_results("TST", original)
    loaded = collector.load_from_cache("TST")

    assert loaded is not None
    assert loaded["members"] == original["members"]
    assert loaded["committees"] == original["committees"]
    assert loaded["strategy_text"] == original["strategy_text"]
    print("PASS test_cache_round_trip")


def test_cache_miss_returns_none():
    """Loading from cache with no file returns None."""
    tmp = tempfile.mkdtemp()
    collector = BoardCompositionCollector(data_dir=tmp)
    assert collector.load_from_cache("NONEXISTENT") is None
    print("PASS test_cache_miss_returns_none")


def test_collect_uses_cache():
    """collect_board_data returns cached data when use_cache=True."""
    tmp = tempfile.mkdtemp()
    collector = BoardCompositionCollector(data_dir=tmp)

    cached_data = {
        "members": [{"name": "Cached Person", "title": "Director",
                      "bio": "", "is_independent": False,
                      "committees": [], "tenure_years": 0.0}],
        "committees": [],
        "strategy_text": "",
    }
    collector._cache_results("CACHE", cached_data)

    result = collector.collect_board_data("CACHE", use_cache=True)
    assert result["members"][0]["name"] == "Cached Person"
    print("PASS test_collect_uses_cache")


# ── Scoring Integration Tests ─────────────────────────────────────────

def test_collector_output_feeds_analyzer():
    """Parsed proxy data can be converted to BoardMember and scored."""
    collector = _make_collector()
    data = collector.parse_proxy_html(SAMPLE_PROXY_HTML)

    members = [
        BoardMember(
            name=m["name"],
            title=m.get("title", "Director"),
            committees=m.get("committees", []),
            bio=m.get("bio", ""),
            is_independent=m.get("is_independent", False),
            tenure_years=m.get("tenure_years", 0.0),
        )
        for m in data["members"]
    ]

    analyzer = BoardCompositionAnalyzer()
    signal = analyzer.analyze_board(
        company_id="test-id",
        ticker="TST",
        members=members,
        committees=data["committees"],
        strategy_text=data["strategy_text"],
    )

    assert Decimal("0") <= signal.governance_score <= Decimal("100")
    assert Decimal("0") <= signal.confidence <= Decimal("0.95")
    assert signal.ticker == "TST"
    print("PASS test_collector_output_feeds_analyzer")


def test_full_sample_scores_above_base():
    """Rich proxy data should produce a score well above the base 20."""
    collector = _make_collector()
    data = collector.parse_proxy_html(SAMPLE_PROXY_HTML)

    members = [
        BoardMember(
            name=m["name"],
            title=m.get("title", "Director"),
            committees=m.get("committees", []),
            bio=m.get("bio", ""),
            is_independent=m.get("is_independent", False),
            tenure_years=m.get("tenure_years", 0.0),
        )
        for m in data["members"]
    ]

    analyzer = BoardCompositionAnalyzer()
    signal = analyzer.analyze_board(
        company_id="test-id",
        ticker="TST",
        members=members,
        committees=data["committees"],
        strategy_text=data["strategy_text"],
    )

    # Sample HTML has tech committee (+15), AI expertise (+20), data officer (+15),
    # independent majority (+10), risk oversight (+10), AI strategy (+10)
    # So score should be significantly above base 20
    assert signal.governance_score > Decimal("40"), (
        f"Expected >40 from rich proxy, got {signal.governance_score}"
    )
    print("PASS test_full_sample_scores_above_base")


def test_empty_proxy_scores_base_only():
    """Empty proxy should produce only the base score of 20."""
    collector = _make_collector()
    data = collector.parse_proxy_html(EMPTY_PROXY_HTML)

    members = [
        BoardMember(
            name=m["name"],
            title=m.get("title", "Director"),
            committees=m.get("committees", []),
            bio=m.get("bio", ""),
            is_independent=m.get("is_independent", False),
            tenure_years=m.get("tenure_years", 0.0),
        )
        for m in data["members"]
    ]

    analyzer = BoardCompositionAnalyzer()
    signal = analyzer.analyze_board(
        company_id="test-id",
        ticker="TST",
        members=members,
        committees=data["committees"],
        strategy_text=data["strategy_text"],
    )

    assert signal.governance_score == Decimal("20")
    print("PASS test_empty_proxy_scores_base_only")


def test_signal_evidence_populated():
    """The GovernanceSignal.evidence list is populated with descriptions."""
    collector = _make_collector()
    data = collector.parse_proxy_html(SAMPLE_PROXY_HTML)

    members = [
        BoardMember(
            name=m["name"],
            title=m.get("title", "Director"),
            committees=m.get("committees", []),
            bio=m.get("bio", ""),
            is_independent=m.get("is_independent", False),
            tenure_years=m.get("tenure_years", 0.0),
        )
        for m in data["members"]
    ]

    analyzer = BoardCompositionAnalyzer()
    signal = analyzer.analyze_board(
        company_id="test-id",
        ticker="TST",
        members=members,
        committees=data["committees"],
        strategy_text=data["strategy_text"],
    )

    assert len(signal.evidence) > 0, "Expected evidence entries"
    print("PASS test_signal_evidence_populated")


# ── Helper method unit tests ──────────────────────────────────────────

def test_guess_title():
    collector = _make_collector()
    assert "Chief Technology Officer" in collector._guess_title(
        "She is the Chief Technology Officer of XYZ."
    )
    assert collector._guess_title("No title here at all") == "Director"
    print("PASS test_guess_title")


def test_extract_tenure():
    collector = _make_collector()
    assert collector._extract_tenure("Appointed since 2015") == 10.0
    assert collector._extract_tenure("No date info") == 0.0
    print("PASS test_extract_tenure")


def test_extract_member_committees():
    collector = _make_collector()
    comms = collector._extract_member_committees(
        "Member of Audit, Technology, and Risk committees"
    )
    comm_lower = [c.lower() for c in comms]
    assert any("audit" in c for c in comm_lower)
    assert any("technology" in c for c in comm_lower)
    assert any("risk" in c for c in comm_lower)
    print("PASS test_extract_member_committees")


# ── Runner ────────────────────────────────────────────────────────────

def main():
    tests = [
        test_parse_proxy_extracts_members,
        test_parse_proxy_extracts_committees,
        test_parse_proxy_extracts_strategy_text,
        test_parse_proxy_independent_detection,
        test_parse_proxy_tenure_extraction,
        test_parse_proxy_member_committees,
        test_parse_empty_proxy,
        test_parse_minimal_proxy_bold_fallback,
        test_parse_returns_all_expected_keys,
        test_cache_round_trip,
        test_cache_miss_returns_none,
        test_collect_uses_cache,
        test_collector_output_feeds_analyzer,
        test_full_sample_scores_above_base,
        test_empty_proxy_scores_base_only,
        test_signal_evidence_populated,
        test_guess_title,
        test_extract_tenure,
        test_extract_member_committees,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL {t.__name__}: {e}")

    print(f"\n{passed}/{len(tests)} tests passed")
    if passed < len(tests):
        sys.exit(1)


if __name__ == "__main__":
    main()
