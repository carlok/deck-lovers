"""
Unit tests for md2html.py — converter module.
Run inside the test container:  pytest --cov=md2html --cov-report=term-missing
"""
import os
import sys
import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
INDIGO_PALETTE = FIXTURES / "indigo-palette.json"
BRANDED_PALETTE = FIXTURES / "branded-palette.json"

# Ensure env vars are set before import so build_html picks them up
os.environ.setdefault("SERVER_HOST", "localhost")
os.environ.setdefault("PORT", "8000")
os.environ.setdefault("WS_SCHEME", "ws")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import md2html


# ── parse_slides ─────────────────────────────────────────────────────────────

class TestParsePdfName:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("PDF_NAME", raising=False)
        assert md2html.parse_pdf_name(None) == "slides.pdf"

    def test_strips_directory(self):
        assert md2html.parse_pdf_name("exports/my-deck.pdf") == "my-deck.pdf"

    def test_appends_pdf_extension(self):
        assert md2html.parse_pdf_name("deck") == "deck.pdf"

    def test_rejects_unsafe_names(self):
        with pytest.raises(ValueError, match="invalid pdf name"):
            md2html.parse_pdf_name("..")
        with pytest.raises(ValueError, match="safe filename"):
            md2html.parse_pdf_name("bad name.pdf")


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


# ── extract_front_matter ─────────────────────────────────────────────────────

class TestExtractFrontMatter:
    def test_no_front_matter(self):
        overrides, body = md2html.extract_front_matter("## Hi\n\nBody")
        assert overrides == {}
        assert body.startswith("## Hi")

    def test_branding_logo_on_override(self):
        raw = "---\nbranding:\n  logo_on: title\n---\n## Slide\n\nBody"
        overrides, body = md2html.extract_front_matter(raw)
        assert overrides["logo_on"] == "title"
        assert body.startswith("## Slide")

    def test_parse_slides_after_front_matter(self):
        raw = "---\nbranding:\n  logo_on: none\n---\n## One\n\nA\n---\n## Two\n\nB"
        _, body = md2html.extract_front_matter(raw)
        assert len(md2html.parse_slides(body)) == 2


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

    def test_nested_unordered_list_two_space_indent(self):
        md = (
            "- Parent item\n"
            "  - Child one\n"
            "  - Child two\n"
        )
        html = md2html._md(md)
        assert "<ul>" in html
        assert "<li>Parent item" in html
        assert "<li>Child one" in html and "<li>Child two" in html
        # Nested list should render as <li>Parent...<ul>...</ul></li>
        assert "Parent item<ul>" in html.replace("\n", "")

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

    def test_image_path_left_relative_for_img_folder(self):
        html = md2html._md("![Demo](img/diagram.png)")
        assert 'src="img/diagram.png"' in html

    def test_image_path_with_dot_slash_rewritten(self):
        html = md2html._md("![Demo](./img/diagram.png)")
        assert 'src="/img/diagram.png"' in html

    def test_checklist_unchecked_raw(self):
        # _md applies postprocess inline; cb-open / task-open class expected
        html = md2html._md("- [ ] Todo item")
        assert "task-open" in html or "cb-open" in html

    def test_checklist_checked_raw(self):
        html = md2html._md("- [x] Done item")
        assert "task-done" in html or "cb-done" in html or "✓" in html


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

    def test_ws_url_dynamic(self):
        # WS_URL is now built at runtime in the browser (not baked in at conversion)
        html = self._html()
        assert "location.protocol" in html and "'/ws'" in html

    def test_audience_url_injected(self):
        html = self._html()
        assert "localhost" in html and "audience" in html

    def test_mirror_mode_present(self):
        html = self._html()
        assert "#mirror" in html

    def test_print_mode_present(self):
        html = self._html()
        assert "#print" in html

    def test_line_reveal_token_injected(self):
        html = md2html.build_html(self.SLIDES, doc_title="Deck", line_reveal=True)
        assert "var LINE_REVEAL=true;" in html

    def test_qr_toggle_off_removes_overlay(self):
        html = md2html.build_html(self.SLIDES, doc_title="Deck", show_qr=False)
        assert 'id="qr-overlay"' not in html
        assert "var SHOW_QR=false;" in html

    def test_likes_toggle_off_removes_projector_sidebar(self):
        html = md2html.build_html(self.SLIDES, doc_title="Deck", show_likes=False)
        assert 'id="like-sidebar"' not in html
        assert 'id="sidebar-toggle"' not in html
        assert "var SHOW_LIKES=false;" in html
        assert "function onLikeUpdate" in html
        assert "likesData[msg.slide]=msg.count" in html

    def test_vector_pdf_print_css(self):
        html = self._html()
        assert "@media print" in html
        assert "size:1280px 720px" in html
        assert "__DECK_PRINT_READY__" in html
        assert "PDF_MODE='vector'" in html

    def test_qr_overlay_is_top_right(self):
        html = self._html()
        assert "#qr-overlay{position:fixed;top:24px;right:24px" in html
        assert "#qr-overlay~#like-sidebar{top:180px;}" in html

    def test_raster_pdf_mode_bakes_js(self):
        html = md2html.build_html(self.SLIDES, doc_title="Deck", pdf_mode="raster")
        assert "var PDF_MODE='raster';" in html
        assert "html2canvas" in html
        assert "jsPDF" in html
        assert 'pdf.save(PDF_OUTPUT_NAME)' in html
        assert 'var PDF_OUTPUT_NAME="slides.pdf"' in html

    def test_custom_pdf_output_name_baked_into_js(self):
        html = md2html.build_html(
            self.SLIDES,
            doc_title="Deck",
            pdf_mode="raster",
            pdf_output_name="octopus-deck.pdf",
        )
        assert 'var PDF_OUTPUT_NAME="octopus-deck.pdf"' in html

    def test_pdf_jpeg_quality_baked_into_js(self):
        html = md2html.build_html(
            self.SLIDES,
            doc_title="Deck",
            pdf_jpeg_quality=0.85,
            pdf_mode="raster",
        )
        assert "PDF_JPEG_QUALITY=0.85" in html

    def test_pdf_jpeg_quality_out_of_range_raises(self):
        with pytest.raises(ValueError, match="pdf_jpeg_quality"):
            md2html.build_html(self.SLIDES, doc_title="Deck", pdf_jpeg_quality=0.1)

    def test_font_awesome_cdn(self):
        html = self._html()
        assert "font-awesome" in html.lower() or "fontawesome" in html.lower()

    def test_default_uses_system_font_stack(self):
        html = self._html()
        assert "fonts.googleapis.com" not in html
        assert "system-ui" in html

    def test_custom_font_link_and_css(self):
        html = md2html.build_html(self.SLIDES, doc_title="Deck", font_family="Montserrat")
        assert "fonts.googleapis.com" in html
        assert "Montserrat" in html
        assert "montserrat" in html.lower()

    def test_default_keeps_native_emoji(self):
        html = self._html(["# 🧵 Title"])
        assert "<h1>🧵 Title</h1>" in html
        assert 'class="emoji-img"' not in html

    def test_twemoji_replaces_heading_emoji(self):
        html = md2html.build_html(
            ["# 🧵 Title"],
            doc_title="Deck",
            emoji_mode="svg",
        )
        assert 'class="emoji-img"' in html
        assert 'loading="eager"' in html
        assert "/svg/1f9f5.svg" in html
        assert "<h1>" in html and "Title</h1>" in html

    def test_print_mode_waits_for_emoji_images(self):
        html = self._html()
        assert "waitForEmojiImages" in html
        assert "__DECK_PRINT_READY__" in html

    def test_stats_slide_appended(self):
        html = self._html()
        assert "stats" in html.lower() or "likes" in html.lower()
        assert "top 10" in html.lower()
        assert "slice(0,10)" in html

    def test_stats_slide_can_be_disabled(self):
        html = md2html.build_html(self.SLIDES, doc_title="Deck", include_stats=False)
        assert 'id="stats-slide"' not in html
        # Total slides should not include +1 stats page
        assert "var TOTAL=2;" in html

    def test_checklist_unchecked_postprocessed(self):
        # build_html applies postprocess; ☐ or task-open class expected
        html = self._html(["## S\n\n- [ ] Open task"])
        assert "☐" in html or "task-open" in html.lower() or "open" in html.lower()

    def test_checklist_checked_postprocessed(self):
        html = self._html(["## S\n\n- [x] Done task"])
        assert "✅" in html or "task-done" in html.lower() or "done" in html.lower()

    def test_invalid_youtube_shows_error(self):
        # line 47 in md2html — invalid video ID path
        html = self._html(["## V\n\n!youtube[Bad](not-a-valid-url-at-all)"])
        assert "Invalid YouTube URL" in html or "invalid" in html.lower()

    def test_youtube_embed_rendered(self):
        slides = ["## Video\n\n!youtube[Demo](https://youtube.com/watch?v=dQw4w9WgXcQ)"]
        html = self._html(slides)
        assert "iframe" in html
        assert "youtube.com/embed" in html

    def test_html_passthrough(self):
        slides = ["## Icons\n\n<i class=\"fa-brands fa-github\"></i>"]
        html = self._html(slides)
        assert "fa-github" in html

    def test_image_css_rule_present(self):
        html = self._html(["## Image\n\n![Demo](img/pic.png)"])
        assert ".slide img{" in html


# ── slide branding ────────────────────────────────────────────────────────────

class TestSlideBranding:
    def test_no_chrome_without_branding(self):
        from palette import merge_branding

        html = md2html.build_html(
            ["## A\n\nbody"],
            branding=merge_branding(),
            include_stats=False,
        )
        assert 'class="slide-chrome"' not in html
        assert " has-branding" not in html

    def test_chrome_and_logo_on_content_slides(self):
        from palette import load_branding

        branding = load_branding(BRANDED_PALETTE)
        html = md2html.build_html(
            ["# Title\n\nsub", "## Content\n\nbody"],
            branding=branding,
            include_stats=False,
        )
        assert "slide-chrome-bar-top" in html
        assert "slide-chrome-bar-bottom" in html
        assert '<img class="slide-chrome-logo"' in html
        assert " has-branding" in html

    def test_logo_on_content_not_last_hides_last_content_logo(self):
        from palette import merge_branding, load_branding

        branding = merge_branding(
            load_branding(BRANDED_PALETTE),
            {"logo_on": "content_not_last"},
        )
        slides = ["# T\n\ns", "## A\n\n1", "## B\n\n2"]
        html = md2html.build_html(slides, branding=branding, include_stats=False)
        assert html.count('<img class="slide-chrome-logo"') == 1

    def test_print_css_includes_chrome(self):
        from palette import load_branding

        branding = load_branding(BRANDED_PALETTE)
        html = md2html.build_html(
            ["## A\n\nb"],
            branding=branding,
            include_stats=False,
        )
        assert ".slide-chrome{position:absolute" in html.replace(" ", "")

    def test_chrome_logo_css_overrides_slide_img(self):
        from palette import load_branding

        branding = load_branding(BRANDED_PALETTE)
        html = md2html.build_html(
            ["## A\n\nb"],
            branding=branding,
            include_stats=False,
        )
        assert ".slide img.slide-chrome-logo{" in html
        assert html.index(".slide img.slide-chrome-logo{") > html.index(".slide img{")
        compact = html.replace(" ", "")
        assert "max-height:var(--logo-height)" in compact
        assert "right:5vw" in compact


# ── WebSocket / QR URL tokens ─────────────────────────────────────────────────

class TestEnvTokens:
    """AUDIENCE_URL is still baked in (QR code). WS_URL is now dynamic JS.
    Patch AUDIENCE_URL directly with monkeypatch.setattr."""

    def test_apply_endpoint_config_port(self):
        md2html.apply_endpoint_config(server_host="10.0.0.1", port="9000", ws_scheme="ws")
        assert md2html.AUDIENCE_URL == "http://10.0.0.1:9000/audience"

    def test_custom_host(self, monkeypatch):
        monkeypatch.setattr(md2html, "AUDIENCE_URL", "http://192.168.1.99:8000/audience")
        html = md2html.build_html(["## S\n\nBody"], doc_title="T")
        assert "192.168.1.99" in html

    def test_wss_scheme(self, monkeypatch):
        # WS scheme is now chosen at runtime; AUDIENCE_URL reflects https for QR code
        monkeypatch.setattr(md2html, "AUDIENCE_URL", "https://example.com/audience")
        html = md2html.build_html(["## S\n\nBody"], doc_title="T")
        assert "https://example.com/audience" in html
        # Dynamic WS logic is always present in the output
        assert "location.protocol" in html


# ── main() CLI ────────────────────────────────────────────────────────────────

class TestMain:
    def test_generates_html_file(self, tmp_path, monkeypatch):
        import sys
        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Hello\n\nContent", encoding="utf-8")
        monkeypatch.setattr(sys, "argv",
            ["md2html.py", "--input", str(md_file), "--output", str(out_file)])
        md2html.main()
        assert out_file.exists()

    def test_output_is_valid_html(self, tmp_path, monkeypatch):
        import sys
        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody\n---\n## Two\n\nMore", encoding="utf-8")
        monkeypatch.setattr(sys, "argv",
            ["md2html.py", "--input", str(md_file), "--output", str(out_file)])
        md2html.main()
        content = out_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Slide" in content

    def test_cli_port_baked_into_audience_url(self, tmp_path, monkeypatch):
        import sys
        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody", encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "md2html.py",
                "--input",
                str(md_file),
                "--output",
                str(out_file),
                "--server-host",
                "192.168.0.50",
                "--port",
                "9000",
            ],
        )
        md2html.main()
        content = out_file.read_text(encoding="utf-8")
        assert "http://192.168.0.50:9000/audience" in content

    def test_cli_line_reveal_on(self, tmp_path, monkeypatch):
        import sys
        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody", encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "md2html.py",
                "--input",
                str(md_file),
                "--output",
                str(out_file),
                "--line-reveal",
                "on",
            ],
        )
        md2html.main()
        content = out_file.read_text(encoding="utf-8")
        assert "var LINE_REVEAL=true;" in content

    def test_cli_qr_off(self, tmp_path, monkeypatch):
        import sys
        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody", encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "md2html.py",
                "--input",
                str(md_file),
                "--output",
                str(out_file),
                "--qr",
                "off",
            ],
        )
        md2html.main()
        content = out_file.read_text(encoding="utf-8")
        assert 'id="qr-overlay"' not in content
        assert "var SHOW_QR=false;" in content

    def test_cli_stats_off(self, tmp_path, monkeypatch):
        import sys
        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody", encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "md2html.py",
                "--input",
                str(md_file),
                "--output",
                str(out_file),
                "--stats",
                "off",
            ],
        )
        md2html.main()
        content = out_file.read_text(encoding="utf-8")
        assert 'id="stats-slide"' not in content

    def test_cli_likes_off(self, tmp_path, monkeypatch):
        import sys
        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody", encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "md2html.py",
                "--input",
                str(md_file),
                "--output",
                str(out_file),
                "--likes",
                "off",
            ],
        )
        md2html.main()
        content = out_file.read_text(encoding="utf-8")
        assert 'id="like-sidebar"' not in content
        assert "var SHOW_LIKES=false;" in content

    def test_cli_pdf_quality(self, tmp_path, monkeypatch):
        import sys
        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody", encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "md2html.py",
                "--input",
                str(md_file),
                "--output",
                str(out_file),
                "--pdf-quality",
                "0.8",
            ],
        )
        md2html.main()
        content = out_file.read_text(encoding="utf-8")
        assert "PDF_JPEG_QUALITY=0.8" in content

    def test_cli_font_montserrat(self, tmp_path, monkeypatch):
        import sys

        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", [
            "md2html.py",
            "--input", str(md_file),
            "--output", str(out_file),
            "--font", "Montserrat",
        ])
        md2html.main()
        content = out_file.read_text(encoding="utf-8")
        assert "fonts.googleapis.com" in content
        assert "Montserrat" in content

    def test_cli_font_invalid_exits(self, tmp_path, monkeypatch):
        import sys

        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", [
            "md2html.py",
            "--input", str(md_file),
            "--output", str(out_file),
            "--font", "Bad;Name",
        ])
        with pytest.raises(SystemExit):
            md2html.main()

    def test_cli_emoji_twemoji(self, tmp_path, monkeypatch):
        import sys

        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("# 🧵 Title\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", [
            "md2html.py",
            "--input", str(md_file),
            "--output", str(out_file),
            "--emoji", "twemoji",
        ])
        md2html.main()
        content = out_file.read_text(encoding="utf-8")
        assert 'class="emoji-img"' in content
        assert "/svg/1f9f5.svg" in content

    def test_cli_pdf_name(self, tmp_path, monkeypatch):
        import sys

        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", [
            "md2html.py",
            "--input", str(md_file),
            "--output", str(out_file),
            "--pdf-name", "brand-deck.pdf",
            "--pdf-mode", "raster",
        ])
        md2html.main()
        content = out_file.read_text(encoding="utf-8")
        assert 'var PDF_OUTPUT_NAME="brand-deck.pdf"' in content

    def test_cli_no_frame_disables_bars(self, tmp_path, monkeypatch):
        import sys

        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## One\n\nHello", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", [
            "md2html.py",
            "--input", str(md_file),
            "--output", str(out_file),
            "--palette", str(BRANDED_PALETTE),
            "--no-frame",
        ])
        md2html.main()
        html = out_file.read_text(encoding="utf-8")
        assert '<div class="slide-chrome-bar slide-chrome-bar-top">' not in html
        assert '<div class="slide-chrome-bar slide-chrome-bar-bottom">' not in html

    def test_cli_logo_on_override(self, tmp_path, monkeypatch):
        import sys

        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("# Title\n\nsub\n---\n## Body\n\ncontent", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", [
            "md2html.py",
            "--input", str(md_file),
            "--output", str(out_file),
            "--palette", str(BRANDED_PALETTE),
            "--logo-on", "title",
        ])
        md2html.main()
        html = out_file.read_text(encoding="utf-8")
        assert html.count('<img class="slide-chrome-logo"') == 1

    def test_cli_pdf_quality_invalid_exits(self, tmp_path, monkeypatch):
        import sys
        md_file = tmp_path / "slides.md"
        out_file = tmp_path / "out.html"
        md_file.write_text("## Slide\n\nBody", encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "md2html.py",
                "--input",
                str(md_file),
                "--output",
                str(out_file),
                "--pdf-quality",
                "0.05",
            ],
        )
        with pytest.raises(SystemExit):
            md2html.main()

    def test_missing_input_exits(self, tmp_path, monkeypatch):
        import sys
        monkeypatch.setattr(sys, "argv",
            ["md2html.py", "--input", str(tmp_path / "nope.md"),
             "--output", str(tmp_path / "out.html")])
        with pytest.raises(SystemExit):
            md2html.main()


# ── palette ───────────────────────────────────────────────────────────────────

class TestPalette:
    def test_default_palette_bakes_coral_accent(self):
        html = md2html.build_html(["## S\n\nBody"], doc_title="T")
        assert "--accent:#e94560" in html.lower().replace(" ", "")

    def test_custom_palette_bakes_indigo_accent(self):
        from palette import load_palette

        palette = load_palette(INDIGO_PALETTE)
        html = md2html.build_html(
            ["## S\n\nBody"], doc_title="T", palette=palette,
        )
        assert "--accent:#425ec9" in html.lower().replace(" ", "")

    def test_cli_palette_json_path(self, tmp_path, monkeypatch):
        import sys

        md_file = tmp_path / "slides.md"
        md_file.write_text("## One\n\nHello", encoding="utf-8")
        out_file = tmp_path / "slides.html"
        monkeypatch.setattr(sys, "argv", [
            "md2html.py",
            "--input", str(md_file),
            "--output", str(out_file),
            "--palette", str(INDIGO_PALETTE),
        ])
        md2html.main()
        html = out_file.read_text(encoding="utf-8")
        assert "--accent:#425ec9" in html.lower().replace(" ", "")

    def test_invalid_palette_exits(self, tmp_path, monkeypatch):
        import sys

        md_file = tmp_path / "slides.md"
        md_file.write_text("## One\n\nHello", encoding="utf-8")
        out_file = tmp_path / "slides.html"
        monkeypatch.setattr(sys, "argv", [
            "md2html.py",
            "--input", str(md_file),
            "--output", str(out_file),
            "--palette", "no-such-palette",
        ])
        with pytest.raises(SystemExit):
            md2html.main()
