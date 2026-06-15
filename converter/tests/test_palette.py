"""Unit tests for palette.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from palette import (  # noqa: E402
    DEFAULT_PALETTE,
    build_font_head_links,
    build_root_css,
    google_fonts_css_url,
    load_palette,
    parse_font_family,
    resolve_palette_path,
    sans_stack,
)

FIXTURES = Path(__file__).parent / "fixtures"
INDIGO_JSON = FIXTURES / "indigo-palette.json"


class TestResolvePalettePath:
    def test_none_returns_none(self):
        assert resolve_palette_path(None) is None
        assert resolve_palette_path("") is None
        assert resolve_palette_path("   ") is None

    def test_absolute_json_path(self):
        path = resolve_palette_path(str(INDIGO_JSON))
        assert path == INDIGO_JSON

    def test_builtin_name_default(self):
        palettes_dir = Path(__file__).resolve().parents[2] / "palettes"
        path = resolve_palette_path("default", palettes_dir=palettes_dir)
        assert path is not None
        assert path.name == "default.json"

    def test_missing_name_raises(self, tmp_path: Path):
        empty = tmp_path / "palettes"
        empty.mkdir()
        with pytest.raises(FileNotFoundError, match="no-such-palette"):
            resolve_palette_path("no-such-palette", palettes_dir=empty)


class TestLoadPalette:
    def test_none_returns_builtin_defaults(self):
        palette = load_palette(None)
        assert palette["accent"].lower() == DEFAULT_PALETTE["accent"].lower()

    def test_json_merges_onto_defaults(self):
        palette = load_palette(INDIGO_JSON)
        assert palette["accent"] == "#425ec9"
        assert palette["success"] == DEFAULT_PALETTE["success"].lower()

    def test_invalid_hex_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"colors": {"accent": "not-a-color"}}), encoding="utf-8")
        with pytest.raises(ValueError, match="must be a"):
            load_palette(bad)

    def test_missing_colors_shape_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"colors": []}), encoding="utf-8")
        with pytest.raises(ValueError, match="expected a 'colors' object"):
            load_palette(bad)


class TestBuildRootCss:
    def test_emits_css_variables(self):
        css = build_root_css(load_palette(INDIGO_JSON))
        assert ":root{" in css
        assert "--accent:#425ec9" in css.lower().replace(" ", "")
        assert "system-ui" in css
        assert "--nav-bg:rgba(" in css
        assert "--sans:" in css

    def test_custom_font_in_sans_stack(self):
        css = build_root_css(load_palette(INDIGO_JSON), "Montserrat")
        assert "montserrat" in css.lower()
        assert "system-ui" in css


class TestFontFamily:
    def test_parse_font_none_aliases(self):
        assert parse_font_family(None) is None
        assert parse_font_family("") is None
        assert parse_font_family("system") is None
        assert parse_font_family("none") is None

    def test_parse_font_name(self):
        assert parse_font_family("Montserrat") == "Montserrat"
        assert parse_font_family("Open Sans") == "Open Sans"

    def test_parse_font_invalid_raises(self):
        with pytest.raises(ValueError, match="letters"):
            parse_font_family("Bad;inject")

    def test_sans_stack_without_custom_font(self):
        stack = sans_stack(None)
        assert "montserrat" not in stack.lower()
        assert "system-ui" in stack

    def test_google_fonts_url_encodes_spaces(self):
        url = google_fonts_css_url("Open Sans")
        assert "family=Open+Sans" in url

    def test_build_font_head_links_empty_without_font(self):
        assert build_font_head_links(None) == ""

    def test_build_font_head_links_includes_stylesheet(self):
        links = build_font_head_links("Montserrat")
        assert "fonts.googleapis.com" in links
        assert "Montserrat" in links
