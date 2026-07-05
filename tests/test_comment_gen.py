"""Tests for comment post-processing guardrails (em-dash strip)."""

import content.comment_gen as cg
from content.comment_gen import _strip_em_dashes


def test_em_dash_replaced_with_spaced_en_dash():
    assert _strip_em_dashes("Communities die quietly—not loudly.") == \
        "Communities die quietly – not loudly."


def test_double_hyphen_replaced():
    assert _strip_em_dashes("Fast--and wrong.") == "Fast – and wrong."


def test_spaced_em_dash_leaves_no_double_spaces():
    result = _strip_em_dashes("Retention — not acquisition — is the game.")
    assert "  " not in result
    assert result == "Retention – not acquisition – is the game."


def test_newlines_preserved_in_multiline_variant():
    assert _strip_em_dashes("line one—x\nline two") == "line one – x\nline two"


def test_text_without_dashes_unchanged():
    text = "A well-known point. Nothing to fix here."
    assert _strip_em_dashes(text) == text


def test_generate_comments_applies_strip(monkeypatch):
    mock_raw = "Great point—here is why.\n===\nSecond--variant.\n===\nThird one, clean."
    monkeypatch.setattr(cg, "complete", lambda **kwargs: mock_raw)
    variants = cg.generate_comments("post text", "a headline", "a niche", rank=False)
    assert len(variants) == 3
    assert all("—" not in v["text"] and "--" not in v["text"] for v in variants)
    assert variants[0]["text"] == "Great point – here is why."
    assert variants[1]["text"] == "Second – variant."
