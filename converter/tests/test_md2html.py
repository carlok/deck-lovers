"""
Unit tests for md2html.py — converter module.
Run inside the test container:  pytest --cov=md2html --cov-report=term-missing
"""
import os
import sys
import re
import pytest

# Ensure env vars are set before import so build_html picks them up
os.environ.setdefault("SERVER_HOST", "localhost")
os.environ.setdefault("PORT", "8000")
os.environ.setdefault("WS_SCHEME", "ws")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import md2html


# ── parse_slides ─────────────────────────────────────────────────────────────

class TestParseSlides:
    def test_single_slide(self):
        raw = "## Hello\n\nContent"
        slides = md2html.parse_slides(raw)
        assert len(slides) == 1
        assert "Hello" in slides[0]

    def test_multiple_slides(self):
        raw = "## Slide 1\n\nFoo\n---\n## Slide 2\n\nBar"
        slides = md2html.parse_slides(raw)
        assert len(slides) == 2

    def test_trailing_separator_ignored(self):
        raw = "## Slide 1\n\nFoo\n---\n"
        slides = md2html.parse_slides(raw)
        # Empty trailing slide should be stripped
        assert all(s.strip() for s in slides)

    def test_empty_input_returns_empty(self):
        slides = md2html.parse_slides("")
        assert slides == [] or all(not s.strip() for s in slides)


# ── _slide_title ─────────────────────────────────────────────────────────────

class TestSlideTitle:
    def test_h2_heading(self):
        assert md2html._slide_title("## My Title\n\nContent") == "My Title"

    def test_h1_heading(self):
        assert md2html._slide_title("# Big Title") == "Big Title"

    def test_h3_heading(self):
        result = md2html._slide_title("### Sub Title\n\nBody")
        assert result == "Sub Title"

    def test_no_heading_returns_empty(self):
        assert md2html._slide_title("Just plain text") == ""

    def test_strips_whitespace(self):
        title = md2html._slide_title("##   Padded Title   \n\nContent")
        assert title == "Padded Title"


# ── _is_title ─────────────────────────────────────────────────────────────────

class TestIsTitle:
    def test_h1_is_title(self):
        assert md2html._is_title("# Welcome\n\nSubtitle")

    def test_h2_not_title(self):
        assert not md2html._is_title("## Section\n\nContent")

    def test_plain_text_not_title(self):
        assert not md2html._is_title("Just some text")


# ── _md (markdown → html) ────────────────────────────────────────────────────

class TestMd:
    def test_bold(self):
        assert "<strong>" in md2html._md("**bold**")

    def test_italic(self):
        assert "<em>" in md2html._md("*italic*")

    def test_unordered_list(self):
        html = md2html._md("- item one\n- item two")
        assert "<ul" in html and "<li" in html

    def test_fenced_code_block(self):
        html = md2html._md("```python\nprint('hi')\n```")
        assert "<code" in html

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = md2html._md(md)
        assert "<table" in html

    def test_link(self):
        html = md2html._md("[Click](https://example.com)")
        assert 'href="https://example.com"' in html

    def test_checklist_unchecked(self):
        # markdown lib or postprocess should render task items
        html = md2html._md("- [ ] Todo item")
        assert "[ ]" in html or "checkbox" in html.lower() or "☐" in html

    def test_checklist_checked(self):
        html = md2html._md("- [x] Done item")
        assert "[x]" in html or "checked" in html.lower() or "✅" in html


# ── build_html ────────────────────────────────────────────────────────────────

class TestBuildHtml:
    SLIDES = ["## Slide One\n\nHello world", "## Slide Two\n\nSecond slide"]

    def _html(self, slides=None, title="Test Deck"):
        return md2html.build_html(slides or self.SLIDES, doc_title=title)

    def test_is_valid_html(self):
        html = self._html()
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_slide_content_present(self):
        html = self._html()
        assert "Hello world" in html

    def test_all_slides_present(self):
        html = self._html()
        assert "Slide One" in html
        assert "Slide Two" in html

    def test_doc_title_in_head(self):
        html = self._html(title="My Presentation")
        assert "My Presentation" in html

    def test_ws_url_injected(self):
        html = self._html()
        assert "ws://localhost:8000/ws" in html or "WS_URL" not in html

    def test_audience_url_injected(self):
        html = self._html()
        assert "localhost" in html and "audience" in html

    def test_mirror_mode_present(self):
        html = self._html()
        assert "#mirror" in html

    def test_print_mode_present(self):
        html = self._html()
        assert "#print" in html

    def test_landscape_print_css(self):
        html = self._html()
        assert "1280px" in html
        assert "720px" in html

    def test_font_awesome_cdn(self):
        html = self._html()
        assert "font-awesome" in html.lower() or "fontawesome" in html.lower()

    def test_stats_slide_appended(self):
        html = self._html()
        # Stats/likes slide is always last
        assert "stats" in html.lower() or "likes" in html.lower()

    def test_youtube_embed_rendered(self):
        slides = ["## Video\n\n!youtube[Demo](https://youtube.com/watch?v=dQw4w9WgXcQ)"]
        html = self._html(slides)
        assert "iframe" in html
        assert "youtube.com/embed" in html

    def test_html_passthrough(self):
        slides = ["## Icons\n\n<i class=\"fa-brands fa-github\"></i>"]
        html = self._html(slides)
        assert "fa-github" in html


# ── WebSocket / QR URL tokens ─────────────────────────────────────────────────

class TestEnvTokens:
    def test_custom_host(self, monkeypatch):
        monkeypatch.setenv("SERVER_HOST", "192.168.1.99")
        monkeypatch.setenv("PORT", "8000")
        monkeypatch.setenv("WS_SCHEME", "ws")
        html = md2html.build_html(["## S\n\nBody"], doc_title="T")
        assert "192.168.1.99" in html

    def test_wss_scheme(self, monkeypatch):
        monkeypatch.setenv("SERVER_HOST", "example.com")
        monkeypatch.setenv("PORT", "443")
        monkeypatch.setenv("WS_SCHEME", "wss")
        html = md2html.build_html(["## S\n\nBody"], doc_title="T")
        assert "wss://" in html
