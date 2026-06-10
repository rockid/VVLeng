"""Tests for collector/normaliser.py."""

import pytest
from collector.normaliser import normalise_posts, normalise_profiles


def test_normalise_posts(sample_post_raw):
    posts = normalise_posts(sample_post_raw)
    assert len(posts) == 2

    # Check field mapping
    assert posts[0]["url"] == "https://www.linkedin.com/posts/123"
    assert posts[0]["text"] == "Excited to share our latest work on AI-powered analytics at the edge."
    assert posts[0]["likes_count"] == 45
    assert posts[0]["comments_count"] == 12
    assert posts[0]["author_name"] == "Alice Zhang"
    assert posts[0]["author_headline"] == "CEO at DataFlow"

    # All posts have UUID ids
    assert len(posts[0]["id"]) == 36  # UUID4 length
    assert len(posts[1]["id"]) == 36


def test_normalise_posts_empty():
    assert normalise_posts([]) == []


def test_normalise_posts_malformed():
    """Malformed items should be skipped with a warning, not crash."""
    raw = [
        {"postUrl": "https://linkedin.com/posts/1", "text": "Good post"},
        {"badField": True},  # no valid fields
        {"postUrl": "https://linkedin.com/posts/3", "text": "Another"},
    ]
    posts = normalise_posts(raw)
    assert len(posts) == 3  # malformed still included with empty fields


def test_normalise_profiles(sample_profile_raw):
    profiles = normalise_profiles(sample_profile_raw)
    assert len(profiles) == 3

    assert profiles[0]["linkedin_urn"] == "urn:li:fsd_profile:abc123"
    assert profiles[0]["full_name"] == "Alice Zhang"
    assert profiles[0]["headline"] == "CEO at DataFlow | AI & Analytics"
    assert profiles[0]["follower_count"] == 5200
    assert profiles[0]["connection_count"] == 850
    assert profiles[0]["last_activity_date"] == "2026-06-08"


def test_normalise_profiles_empty():
    assert normalise_profiles([]) == []