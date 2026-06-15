"""Unit tests for palette.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from palette import (  # noqa: E402
    DEFAULT_PALETTE,
    build_root_css,
    load_palette,
    resolve_palette_path,
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
        assert "--nav-bg:rgba(" in css
        assert "--sans:" in css
