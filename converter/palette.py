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

DEFAULT_BRANDING: dict[str, Any] = {
    "frame_top": False,
    "frame_bottom": False,
    "frame_height": "5px",
    "frame_color": "accent",
    "logo": "",
    "logo_height": "40px",
    "logo_position": "top-right",
    "logo_on": "none",
}

LOGO_ON_VALUES = frozenset({"all", "title", "content", "none", "content_not_last"})
LOGO_POSITION_VALUES = frozenset({"top-right"})
_CSS_LENGTH_RE = re.compile(r"^\d+(\.\d+)?(px|rem|em|vh|vw|%)$")

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_FONT_NAME_RE = re.compile(r"^[\w][\w\s\-]*$")

_SYSTEM_SANS_FALLBACK = (
    'system-ui,-apple-system,"Segoe UI","Noto Color Emoji",'
    '"Apple Color Emoji","Segoe UI Emoji",sans-serif'
)

# Weights loaded from Google Fonts for slide headings and body.
_GOOGLE_FONT_WEIGHTS = "ital,wght@0,400;0,600;0,700;0,800;1,400"


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


def _validate_css_length(value: str, key: str) -> str:
    raw = value.strip()
    if not _CSS_LENGTH_RE.match(raw):
        raise ValueError(
            f"branding key '{key}' must be a CSS length (e.g. 5px, 2.5rem), got: {value!r}"
        )
    return raw


def _read_palette_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"palette {path}: expected a JSON object at top level")
    return data


def _parse_branding_dict(raw: dict[str, Any], *, source: str) -> dict[str, Any]:
    """Merge and validate a branding mapping onto DEFAULT_BRANDING."""
    merged: dict[str, Any] = dict(DEFAULT_BRANDING)
    for key, value in raw.items():
        if key not in DEFAULT_BRANDING:
            raise ValueError(f"{source}: unknown branding key '{key}'")
        merged[key] = value

    merged["frame_top"] = bool(merged["frame_top"])
    merged["frame_bottom"] = bool(merged["frame_bottom"])
    merged["frame_height"] = _validate_css_length(str(merged["frame_height"]), "frame_height")
    merged["logo_height"] = _validate_css_length(str(merged["logo_height"]), "logo_height")

    frame_color = str(merged["frame_color"]).strip()
    if frame_color in {"accent", "dark"}:
        merged["frame_color"] = frame_color
    else:
        merged["frame_color"] = _validate_hex(frame_color, "frame_color")

    logo = str(merged["logo"]).strip()
    merged["logo"] = logo

    logo_on = str(merged["logo_on"]).strip().lower()
    if logo_on not in LOGO_ON_VALUES:
        raise ValueError(
            f"{source}: branding.logo_on must be one of {sorted(LOGO_ON_VALUES)}, got: {logo_on!r}"
        )
    merged["logo_on"] = logo_on

    logo_position = str(merged["logo_position"]).strip().lower()
    if logo_position not in LOGO_POSITION_VALUES:
        raise ValueError(
            f"{source}: branding.logo_position must be one of {sorted(LOGO_POSITION_VALUES)}, "
            f"got: {logo_position!r}"
        )
    merged["logo_position"] = logo_position

    return merged


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

    data = _read_palette_json(path)
    colors = data.get("colors", data)
    if not isinstance(colors, dict):
        raise ValueError(f"palette {path}: expected a 'colors' object or top-level color map")

    for key, value in colors.items():
        if key in DEFAULT_BRANDING or key == "branding":
            continue
        if not isinstance(value, str):
            raise ValueError(f"palette {path}: color '{key}' must be a string")
        merged[key] = _validate_hex(value, key)

    for key, value in merged.items():
        merged[key] = _validate_hex(value, key)

    return merged


def load_branding(path: Path | None) -> dict[str, Any]:
    """Load optional branding block from a palette JSON file."""
    if path is None:
        return dict(DEFAULT_BRANDING)

    data = _read_palette_json(path)
    branding = data.get("branding")
    if branding is None:
        return dict(DEFAULT_BRANDING)
    if not isinstance(branding, dict):
        raise ValueError(f"palette {path}: expected 'branding' to be an object")
    return _parse_branding_dict(branding, source=f"palette {path}")


def merge_branding(*layers: dict[str, Any] | None) -> dict[str, Any]:
    """Merge branding dicts left-to-right; later layers override earlier ones."""
    merged = dict(DEFAULT_BRANDING)
    for layer in layers:
        if not layer:
            continue
        for key, value in layer.items():
            if key in merged:
                merged[key] = value
    return _parse_branding_dict(merged, source="merged branding")


def branding_is_active(branding: dict[str, Any] | None) -> bool:
    """True when any frame bar or logo branding should render."""
    if not branding:
        return False
    if branding.get("frame_top") or branding.get("frame_bottom"):
        return True
    return bool(str(branding.get("logo", "")).strip())


def resolve_frame_color_css(frame_color: str, palette: dict[str, str]) -> str:
    """Return a CSS color value for frame bars."""
    if frame_color == "accent":
        return "var(--accent)"
    if frame_color == "dark":
        return "var(--dark)"
    return frame_color


def parse_font_family(value: str | None) -> str | None:
    """Return a Google Font family name, or None for the system UI stack.

    Empty strings and aliases (system, default, none) disable a custom font.
    """
    if value is None:
        return None
    raw = value.strip()
    if not raw or raw.lower() in {"system", "system-ui", "default", "none"}:
        return None
    if not _FONT_NAME_RE.match(raw):
        raise ValueError(
            f"font family must contain only letters, digits, spaces, or hyphens, got: {value!r}"
        )
    return raw


def parse_logo_on(value: str | None) -> str | None:
    """Validate --logo-on CLI value."""
    if value is None:
        return None
    raw = value.strip().lower()
    if not raw:
        return None
    if raw not in LOGO_ON_VALUES:
        raise ValueError(
            f"logo_on must be one of {sorted(LOGO_ON_VALUES)}, got: {value!r}"
        )
    return raw


def sans_stack(font_family: str | None = None) -> str:
    """Build the CSS font-family value for --sans."""
    if not font_family:
        return _SYSTEM_SANS_FALLBACK
    return f'"{font_family}",{_SYSTEM_SANS_FALLBACK}'


def google_fonts_css_url(font_family: str) -> str:
    """Google Fonts CSS2 URL for a family name (e.g. Montserrat, Open Sans)."""
    family_param = font_family.strip().replace(" ", "+")
    return (
        f"https://fonts.googleapis.com/css2?family={family_param}:"
        f"{_GOOGLE_FONT_WEIGHTS}&display=swap"
    )


def build_font_head_links(font_family: str | None) -> str:
    """Return <link> tags for Google Fonts, or empty string when using system fonts."""
    if not font_family:
        return ""
    url = google_fonts_css_url(font_family)
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link rel="stylesheet" href="{url}">'
    )


def build_root_css(
    palette: dict[str, str],
    font_family: str | None = None,
    branding: dict[str, Any] | None = None,
) -> str:
    """Emit :root { … } block for slide deck CSS variables."""
    accent = palette["accent"]
    dark = palette["dark"]
    sans = sans_stack(font_family)
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
        f"  --sans:{sans};",
        "  --ease:cubic-bezier(.4,0,.2,1);--dur:360ms;",
    ]
    if branding_is_active(branding):
        assert branding is not None
        frame_color = resolve_frame_color_css(str(branding["frame_color"]), palette)
        lines.append(f"  --frame-bar-height:{branding['frame_height']};")
        lines.append(f"  --frame-bar-color:{frame_color};")
        lines.append(f"  --logo-height:{branding['logo_height']};")
    lines.append("}")
    return "\n".join(lines)
