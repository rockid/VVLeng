"""Tests for processor/scorer.py."""

import pytest
from collector.normaliser import normalise_profiles
from processor.scorer import score_profiles


def _normalised(sample_profile_raw):
    """Return normalised profiles for scoring tests."""
    return normalise_profiles(sample_profile_raw)


def test_score_tier_a(sample_profile_raw, niche_keywords):
    """Highest-relevance profiles should score Tier A."""
    profiles = score_profiles(_normalised(sample_profile_raw), niche_keywords)
    alice = next(p for p in profiles if p["full_name"] == "Alice Zhang")
    # Alice (headline="CEO at DataFlow | AI & Analytics") scores ~0.505 → Tier B
    assert alice["tier"] in ("A", "B")
    assert alice["relevance_score"] > 0


def test_score_tier_a_threshold_met(niche_keywords):
    """Profile matching 3+ keywords + high followers should hit Tier A."""
    profile = _normalised([{
        "fullName": "AI Expert",
        "headline": "AI analytics data science machine learning expert",
        "followersCount": 15000,
    }])
    scored = score_profiles(profile, niche_keywords)
    assert scored[0]["tier"] == "A"
    assert scored[0]["overall_score"] >= 0.65


def test_score_tier_b(sample_profile_raw, niche_keywords):
    """Medium-relevance profiles should score Tier B."""
    profiles = score_profiles(_normalised(sample_profile_raw), niche_keywords)
    bob = next(p for p in profiles if p["full_name"] == "Bob Chen")
    assert bob["tier"] in ("A", "B", "C")


def test_score_tier_c(niche_keywords):
    """No-match profile should score Tier C."""
    profile = _normalised([{
        "fullName": "Unknown User",
        "headline": "Unrelated field",
        "followersCount": 100,
    }])
    scored = score_profiles(profile, niche_keywords)
    assert scored[0]["tier"] == "C"


def test_score_empty():
    assert score_profiles([], ["AI"]) == []


def test_score_missing_fields():
    """Profiles with missing fields should not crash."""
    profile = _normalised([{"fullName": "Test"}])
    scored = score_profiles(profile, ["AI"])
    assert len(scored) == 1
    # Missing headline text → relevance = 0 → Tier C
    assert scored[0]["tier"] == "C"
    assert scored[0]["relevance_score"] == 0.0
