"""Tests for processor/dedup.py."""

import pytest
from processor.dedup import dedup_profiles


def test_dedup_removes_duplicates():
    profiles = [
        {"linkedin_urn": "urn:li:abc", "full_name": "Alice Zhang", "follower_count": 5000},
        {"linkedin_urn": "urn:li:abc", "full_name": "Alice Zhang", "follower_count": 5200},
        {"linkedin_urn": "urn:li:def", "full_name": "Bob Chen", "follower_count": 3800},
    ]
    result = dedup_profiles(profiles)
    assert len(result) == 2
    # Should keep the one with higher follower count
    alice = next(p for p in result if p["linkedin_urn"] == "urn:li:abc")
    assert alice["follower_count"] == 5200


def test_dedup_no_urn():
    """Dedup by name when URN is missing."""
    profiles = [
        {"full_name": "Alice Zhang", "follower_count": 5000},
        {"full_name": "Alice Zhang", "follower_count": 5200},
        {"full_name": "Bob Chen", "follower_count": 3800},
    ]
    result = dedup_profiles(profiles)
    assert len(result) == 2


def test_dedup_empty():
    assert dedup_profiles([]) == []


def test_dedup_no_duplicates(sample_profile_raw):
    result = dedup_profiles(sample_profile_raw)
    assert len(result) == len(sample_profile_raw)


def test_dedup_all_same():
    """All identical profiles should reduce to 1."""
    profiles = [
        {"linkedin_urn": "urn:li:abc", "full_name": "Alice Zhang"},
        {"linkedin_urn": "urn:li:abc", "full_name": "Alice Zhang"},
        {"linkedin_urn": "urn:li:abc", "full_name": "Alice Zhang"},
    ]
    result = dedup_profiles(profiles)
    assert len(result) == 1