"""Tests for the career-transition / HR-topic noise classifier."""

from processor.post_scorer import _noise_reason


def test_obvious_career_change_post_caught():
    text = (
        "After 6 years at Acme Corp, I've decided it's time for something new. "
        "I was laid off in March and the job search has taught me more about "
        "resilience than any role ever did. #OpenToWork"
    )
    assert _noise_reason(text) == "career transition / job seeking"


def test_hr_topic_dominant_post_caught():
    # No recruiting-pattern words (e.g. "hiring") — must be caught purely by
    # the 2+ HR-marker rule.
    text = (
        "Unpopular opinion: talent acquisition gets blamed for slow processes, "
        "but recruiters are usually stuck waiting on feedback loops they don't "
        "control."
    )
    assert _noise_reason(text) == "HR-topic dominant"


def test_legit_community_post_not_caught():
    text = (
        "Most communities don't die from conflict, they die from silence. "
        "We rebuilt our onboarding around one question: what would make you "
        "come back tomorrow? Retention doubled in a quarter. The lesson: "
        "engagement is designed, not hoped for."
    )
    assert _noise_reason(text) == ""


def test_borderline_single_hr_mention_not_caught():
    # One passing HR-marker mention inside genuine community-ops content must
    # NOT classify the post as noise (the 2-hit rule).
    text = (
        "Community managers end up doing everything: events, moderation, even "
        "helping members connect with a recruiter now and then. The role needs "
        "clearer boundaries, and community ROI metrics would help define them."
    )
    assert _noise_reason(text) == ""


def test_anchored_next_chapter_caught():
    text = (
        "After two decades, I am moving on from Oracle and beginning the next "
        "chapter of my career. Thank you to everyone I worked with."
    )
    assert _noise_reason(text) == "career transition / job seeking"


def test_figurative_next_chapter_not_caught():
    # "next chapter" as a business metaphor must NOT classify the post as a
    # career transition (validated false positive on the 2026-06-22 corpus).
    text = (
        "Community is the moat. This realization shapes how I think about the "
        "next chapter of customer marketing: members, not audiences."
    )
    assert _noise_reason(text) == ""


def test_borderline_alumni_years_phrasing_not_caught():
    # "years" phrasing WITHOUT the "at <company>" anchor is common in alumni /
    # community content and must not fire the career-transition pattern.
    text = (
        "We surveyed members who stayed active for 5 years. After 5 years, the "
        "ones still engaged all had one thing in common: a role in the "
        "community, not just a seat."
    )
    assert _noise_reason(text) == ""
