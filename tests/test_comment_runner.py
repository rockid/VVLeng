"""Tests for the HTML comment-runner builder."""

import csv

from planner.comment_runner import build_comment_runner


def _write_sheet(path, rows):
    fields = ["rank", "author", "tier", "rank_score", "gate_reason", "post_url",
              "post_text", "top_confidence", "top_reason",
              "comment_1", "comment_2", "comment_3"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_builds_html_next_to_sheet_with_derived_name(tmp_path):
    sheet = tmp_path / "comment_sheet_2026-07-05.csv"
    _write_sheet(sheet, [{
        "rank": "1", "author": "Jane Doe", "tier": "tier1", "rank_score": "0.81",
        "gate_reason": "ICP fit", "post_url": "https://linkedin.com/posts/x",
        "post_text": "Retention is the game.", "top_confidence": "5",
        "top_reason": "sharpest", "comment_1": "Top pick.",
        "comment_2": "Alt one.", "comment_3": "",
    }])
    out = build_comment_runner(str(sheet))
    assert out.endswith("comment_runner_2026-07-05.html")
    html = open(out, encoding="utf-8").read()
    assert "Jane Doe" in html
    assert "Top pick." in html
    assert "Comment Runner — 2026-07-05" in html


def test_script_closing_tag_in_data_is_escaped(tmp_path):
    sheet = tmp_path / "comment_sheet_2026-07-05.csv"
    _write_sheet(sheet, [{
        "rank": "1", "author": "A", "tier": "tier2", "rank_score": "0.5",
        "gate_reason": "", "post_url": "u",
        "post_text": "evil </script><script>alert(1)</script>",
        "top_confidence": "3", "top_reason": "",
        "comment_1": "c1", "comment_2": "", "comment_3": "",
    }])
    html = open(build_comment_runner(str(sheet)), encoding="utf-8").read()
    # the raw closing tag from post data must never appear unescaped in the JSON blob
    assert "evil </script>" not in html
    assert "evil <\\/script>" in html


def test_explicit_out_path_and_empty_sheet(tmp_path):
    sheet = tmp_path / "comment_sheet_2026-07-05.csv"
    _write_sheet(sheet, [])
    target = tmp_path / "custom_runner.html"
    out = build_comment_runner(str(sheet), out_path=str(target))
    assert out == str(target)
    assert "const DATA = []" in open(out, encoding="utf-8").read()
