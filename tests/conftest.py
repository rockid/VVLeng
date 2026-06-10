"""pytest shared fixtures."""

import pytest


@pytest.fixture
def sample_post_raw():
    """Sample raw Apify post-search output (pre-normalisation)."""
    return [
        {
            "postUrl": "https://www.linkedin.com/posts/123",
            "text": "Excited to share our latest work on AI-powered analytics at the edge.",
            "likesCount": 45,
            "commentsCount": 12,
            "postedAt": "2026-06-10T08:00:00Z",
            "authorName": "Alice Zhang",
            "authorHeadline": "CEO at DataFlow",
            "authorUrl": "https://www.linkedin.com/in/alice-zhang",
        },
        {
            "postUrl": "https://www.linkedin.com/posts/456",
            "text": "Why Python is still the best language for data science in 2026.",
            "likesCount": 120,
            "commentsCount": 34,
            "postedAt": "2026-06-09T22:30:00Z",
            "authorName": "Bob Chen",
            "authorHeadline": "ML Engineer at ScaleAI",
            "authorUrl": "https://www.linkedin.com/in/bob-chen",
        },
    ]


@pytest.fixture
def sample_profile_raw():
    """Sample raw Apify profile-scraper output (pre-normalisation)."""
    return [
        {
            "profileId": "urn:li:fsd_profile:abc123",
            "fullName": "Alice Zhang",
            "headline": "CEO at DataFlow | AI & Analytics",
            "followersCount": 5200,
            "connectionsCount": 850,
            "lastActivityDate": "2026-06-08",
        },
        {
            "profileId": "urn:li:fsd_profile:def456",
            "fullName": "Bob Chen",
            "headline": "Senior ML Engineer at ScaleAI | NLP",
            "followersCount": 3800,
            "connectionsCount": 1200,
            "lastActivityDate": "2026-06-01",
        },
        {
            "profileId": "urn:li:fsd_profile:ghi789",
            "fullName": "Carol Li",
            "headline": "Data Scientist at InsightLab",
            "followersCount": 900,
            "connectionsCount": 450,
            "lastActivityDate": "2026-05-20",
        },
    ]


@pytest.fixture
def niche_keywords():
    return ["AI", "analytics", "data science", "machine learning"]