"""Unit tests for palette.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from palette import (  # noqa: E402
    DEFAULT_BRANDING,
    DEFAULT_PALETTE,
    branding_is_active,
    build_font_head_links,
    build_root_css,
    google_fonts_css_url,
    load_branding,
    load_palette,
    merge_branding,
    parse_font_family,
    parse_logo_on,
    resolve_frame_color_css,
    resolve_palette_path,
    sans_stack,
)

FIXTURES = Path(__file__).parent / "fixtures"
INDIGO_JSON = FIXTURES / "indigo-palette.json"
BRANDED_JSON = FIXTURES / "branded-palette.json"


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
        assert google_fonts_css_url("Montserrat") in links
        assert "Montserrat" in links


class TestBranding:
    def test_default_branding_inactive(self):
        branding = load_branding(None)
        assert branding == DEFAULT_BRANDING
        assert not branding_is_active(branding)

    def test_load_branding_from_fixture(self):
        branding = load_branding(BRANDED_JSON)
        assert branding["frame_top"] is True
        assert branding["logo"] == "img/test-logo.png"
        assert branding["logo_on"] == "content"

    def test_invalid_logo_on_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(
            json.dumps({"branding": {"logo_on": "sometimes"}}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="logo_on"):
            load_branding(bad)

    def test_frame_color_accent_resolves_to_css_var(self):
        palette = load_palette(INDIGO_JSON)
        branding = load_branding(BRANDED_JSON)
        assert resolve_frame_color_css(str(branding["frame_color"]), palette) == "var(--accent)"

    def test_frame_color_hex(self, tmp_path: Path):
        path = tmp_path / "hex.json"
        path.write_text(
            json.dumps({"branding": {"frame_color": "#AABBCC"}}),
            encoding="utf-8",
        )
        branding = load_branding(path)
        assert branding["frame_color"] == "#aabbcc"

    def test_merge_branding_cli_overrides_palette(self):
        base = load_branding(BRANDED_JSON)
        merged = merge_branding(base, {"logo_on": "none"})
        assert merged["logo_on"] == "none"
        assert merged["frame_top"] is True

    def test_build_root_css_includes_frame_vars_when_active(self):
        palette = load_palette(BRANDED_JSON)
        branding = load_branding(BRANDED_JSON)
        css = build_root_css(palette, branding=branding)
        assert "--frame-bar-height:5px" in css.replace(" ", "")
        assert "--frame-bar-color:var(--accent)" in css.replace(" ", "")
        assert "--logo-height:40px" in css.replace(" ", "")

    def test_build_root_css_omits_frame_vars_when_inactive(self):
        css = build_root_css(load_palette(INDIGO_JSON), branding=DEFAULT_BRANDING)
        assert "--frame-bar-height" not in css

    def test_parse_logo_on_validates(self):
        assert parse_logo_on("content_not_last") == "content_not_last"
        with pytest.raises(ValueError, match="logo_on"):
            parse_logo_on("bogus")
