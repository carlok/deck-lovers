"""Tests for Twemoji substitution."""

import pytest

from emoji_img import (
    parse_emoji_mode,
    substitute_twemoji,
    twemoji_asset_url,
    twemoji_codepoint,
    twemoji_img_tag,
)


class TestParseEmojiMode:
    def test_default_off(self):
        assert parse_emoji_mode(None) is None
        assert parse_emoji_mode("") is None
        assert parse_emoji_mode("off") is None
        assert parse_emoji_mode("native") is None

    def test_twemoji_aliases(self):
        assert parse_emoji_mode("twemoji") == "svg"
        assert parse_emoji_mode("svg") == "svg"
        assert parse_emoji_mode("on") == "svg"

    def test_png_mode(self):
        assert parse_emoji_mode("png") == "png"
        assert parse_emoji_mode("twemoji-png") == "png"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="emoji mode"):
            parse_emoji_mode("not-a-mode")


class TestTwemojiCodepoint:
    def test_single_emoji(self):
        assert twemoji_codepoint("🧵") == "1f9f5"

    def test_zwj_sequence(self):
        assert twemoji_codepoint("👨‍👩‍👧") == "1f468-200d-1f469-200d-1f467"

    def test_flag(self):
        assert twemoji_codepoint("🇮🇹") == "1f1ee-1f1f9"


class TestTwemojiUrls:
    def test_svg_url(self):
        url = twemoji_asset_url("🧵", "svg")
        assert url.endswith("/svg/1f9f5.svg")
        assert "twemoji" in url

    def test_png_url(self):
        url = twemoji_asset_url("🧵", "png")
        assert url.endswith("/72x72/1f9f5.png")


class TestSubstituteTwemoji:
    def test_replaces_in_plain_text(self):
        out = substitute_twemoji("Hello 🧵 world")
        assert 'class="emoji-img"' in out
        assert "/svg/1f9f5.svg" in out
        assert "<img" in out

    def test_img_tag_escapes_alt(self):
        tag = twemoji_img_tag('🧵')
        assert 'alt="🧵"' in tag
        assert "emoji-img" in tag
