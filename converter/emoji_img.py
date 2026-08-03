"""Replace Unicode emoji with Twemoji SVG/PNG for crisp HTML and PDF rendering."""

from __future__ import annotations

import html as html_module
from typing import Literal

import emoji

TwemojiFormat = Literal["svg", "png"]

_TWEMOJI_VERSION = "14.0.2"
_TWEMOJI_CDN = f"https://cdn.jsdelivr.net/gh/twitter/twemoji@{_TWEMOJI_VERSION}/assets"

# Aliases that keep native OS emoji fonts (default).
_EMOJI_OFF = frozenset({"", "off", "none", "native", "system", "default"})


def parse_emoji_mode(value: str | None) -> str | None:
    """Return a Twemoji mode ('svg' or 'png') or None for native emoji.

    Args:
        value: CLI/env string such as ``twemoji``, ``svg``, ``png``, or ``off``.

    Returns:
        ``'svg'``, ``'png'``, or ``None`` when native emoji should be kept.

    Raises:
        ValueError: If the mode string is not recognized.
    """
    if value is None:
        return None
    raw = value.strip().lower()
    if raw in _EMOJI_OFF:
        return None
    if raw in {"twemoji", "on", "yes", "true", "1", "svg"}:
        return "svg"
    if raw in {"twemoji-png", "png", "raster"}:
        return "png"
    raise ValueError(
        f"emoji mode must be twemoji, svg, png, or off/none/native, got: {value!r}"
    )


def twemoji_codepoint(emoji_chars: str) -> str:
    """Build the Twemoji asset filename stem for a grapheme cluster.

    Matches Twemoji's ``toCodePoint`` (keeps U+FE0F out, keeps U+200D ZWJ in).
    """
    parts: list[str] = []
    for ch in emoji_chars:
        if ch == "\ufe0f":
            continue
        parts.append(f"{ord(ch):x}")
    return "-".join(parts)


def twemoji_asset_url(emoji_chars: str, fmt: TwemojiFormat = "svg") -> str:
    """Public CDN URL for a Twemoji asset."""
    code = twemoji_codepoint(emoji_chars)
    if fmt == "svg":
        return f"{_TWEMOJI_CDN}/svg/{code}.svg"
    return f"{_TWEMOJI_CDN}/72x72/{code}.png"


def twemoji_img_tag(emoji_chars: str, fmt: TwemojiFormat = "svg") -> str:
    """Inline ``<img>`` sized with ``em`` units to match surrounding text."""
    url = twemoji_asset_url(emoji_chars, fmt)
    alt = html_module.escape(emoji_chars, quote=True)
    src = html_module.escape(url, quote=True)
    return (
        f'<img class="emoji-img" src="{src}" alt="{alt}" '
        f'draggable="false" loading="eager" decoding="async">'
    )


def substitute_twemoji(text: str, fmt: TwemojiFormat = "svg") -> str:
    """Replace every emoji grapheme in *text* with a Twemoji ``<img>`` tag."""

    def _replace(chars: str, _data: dict | None = None) -> str:
        return twemoji_img_tag(chars, fmt)

    return emoji.replace_emoji(text, replace=_replace)
