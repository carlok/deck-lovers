#!/usr/bin/env python3
"""Load slide-deck color palettes from JSON and emit CSS custom properties."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Built-in deck-lovers look (warm cream + coral accent).
DEFAULT_PALETTE: dict[str, str] = {
    "accent": "#E94560",
    "accent-hover": "#C73E54",
    "success": "#2ECC71",
    "warning": "#F39C12",
    "dark": "#1A2333",
    "text": "#2C3E50",
    "muted": "#7F8C8D",
    "bg": "#FAFAF8",
    "bg-cream": "#FFF9F0",
    "border": "#E8E4DF",
    "link": "#3498DB",
    "pre-text": "#CBD5E1",
    "table-stripe": "#F7F5F2",
    "table-hover": "#FFF0F2",
    "title-gradient-mid": "#FFF0F3",
    "title-gradient-end": "#FFF8EC",
}

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def _expand_shorthand_hex(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        return "#" + "".join(c * 2 for c in h)
    return "#" + h.lower()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = _expand_shorthand_hex(hex_color).lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r},{g},{b},{alpha})"


def _validate_hex(value: str, key: str) -> str:
    if not _HEX_RE.match(value):
        raise ValueError(f"palette key '{key}' must be a #RGB or #RRGGBB hex color, got: {value!r}")
    return _expand_shorthand_hex(value)


def resolve_palette_path(
    palette_arg: str | None,
    *,
    palettes_dir: Path | None = None,
) -> Path | None:
    """Resolve CLI/env palette to a JSON file path, or None for built-in default."""
    if not palette_arg:
        return None
    raw = palette_arg.strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_file():
        return path
    if path.suffix.lower() != ".json":
        candidates: list[Path] = []
        if palettes_dir is not None:
            candidates.append(palettes_dir / f"{raw}.json")
        here = Path(__file__).resolve().parent
        candidates.extend([
            here / "palettes" / f"{raw}.json",
            here.parent / "palettes" / f"{raw}.json",
            Path("/palettes") / f"{raw}.json",
        ])
        for candidate in candidates:
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"palette not found: {palette_arg}")


def load_palette(path: Path | None) -> dict[str, str]:
    """Load and merge a palette JSON file onto DEFAULT_PALETTE."""
    merged = dict(DEFAULT_PALETTE)
    if path is None:
        return merged

    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    colors = data.get("colors", data)
    if not isinstance(colors, dict):
        raise ValueError(f"palette {path}: expected a 'colors' object or top-level color map")

    for key, value in colors.items():
        if not isinstance(value, str):
            raise ValueError(f"palette {path}: color '{key}' must be a string")
        merged[key] = _validate_hex(value, key)

    for key, value in merged.items():
        merged[key] = _validate_hex(value, key)

    return merged


def build_root_css(palette: dict[str, str]) -> str:
    """Emit :root { … } block for slide deck CSS variables."""
    accent = palette["accent"]
    dark = palette["dark"]
    lines = [
        ":root{",
        f"  --accent:{accent};--accent-hover:{palette['accent-hover']};",
        f"  --success:{palette['success']};--warning:{palette['warning']};",
        f"  --dark:{dark};--text:{palette['text']};--muted:{palette['muted']};",
        f"  --bg:{palette['bg']};--bg-cream:{palette['bg-cream']};",
        f"  --border:{palette['border']};--link:{palette['link']};",
        f"  --pre-text:{palette['pre-text']};",
        f"  --table-stripe:{palette['table-stripe']};--table-hover:{palette['table-hover']};",
        f"  --title-gradient-mid:{palette['title-gradient-mid']};",
        f"  --title-gradient-end:{palette['title-gradient-end']};",
        f"  --nav-bg:{_rgba(dark, 0.88)};--qr-bg:{_rgba(dark, 0.9)};",
        f"  --sidebar-bg:{_rgba(dark, 0.94)};",
        f"  --accent-shadow:{_rgba(accent, 0.32)};--accent-22:{_rgba(accent, 0.22)};",
        f"  --link-30:{_rgba(palette['link'], 0.3)};",
        '  --mono:"SF Mono","Fira Code","Consolas",monospace;',
        '  --sans:system-ui,-apple-system,"Segoe UI","Noto Color Emoji",'
        '"Apple Color Emoji","Segoe UI Emoji",sans-serif;',
        "  --ease:cubic-bezier(.4,0,.2,1);--dur:360ms;",
        "}",
    ]
    return "\n".join(lines)
