#!/usr/bin/env python3
"""
tex_extract.py — Extract Beamer frames from a LaTeX file and write clean Markdown.

Each \begin{frame}...\end{frame} becomes a ## slide.
Frame content is converted to readable HTML/Markdown that pandoc can pass to Reveal.js.

Usage:
    python tex_extract.py --input source/slides.tex --output workspace/slides.md
"""

import re
import sys
import argparse
from pathlib import Path

# ── FontAwesome → emoji fallback ─────────────────────────────────────────────
FA = {
    'faRobot': '🤖', 'faBrain': '🧠', 'faIndustry': '🏭', 'faPaintBrush': '🎨',
    'faShield': '🛡️', 'faUser': '👤', 'faUsers': '👥', 'faGlobe': '🌐',
    'faCloud': '☁️', 'faDatabase': '🗄️', 'faCode': '💻', 'faLock': '🔒',
    'faKey': '🔑', 'faSearch': '🔍', 'faCheck': '✓', 'faTimes': '✗',
    'faExclamationTriangle': '⚠️', 'faWarning': '⚠️', 'faInfo': 'ℹ️',
    'faArrowRight': '→', 'faArrowLeft': '←', 'faStar': '⭐', 'faHeart': '❤️',
    'faThumbsUp': '👍', 'faThumbsDown': '👎', 'faHome': '🏠', 'faFile': '📄',
    'faEnvelope': '✉️', 'faPlay': '▶', 'faTrash': '🗑️', 'faEdit': '✏️',
    'faPlus': '➕', 'faMinus': '➖', 'faChartBar': '📊', 'faChartLine': '📈',
    'faServer': '🖥️', 'faNetworkWired': '🔗', 'faCog': '⚙️', 'faCogs': '⚙️',
    'faLink': '🔗', 'faExternalLink': '↗️', 'faQuoteLeft': '"', 'faQuoteRight': '"',
    'faBolt': '⚡', 'faFire': '🔥', 'faLeaf': '🌿', 'faTree': '🌳',
    'faFlag': '🚩', 'faMap': '🗺️', 'faComments': '💬', 'faComment': '💬',
}


# ── LaTeX helpers ──────────────────────────────────────────────────────────────

def extract_arg(text, pos):
    """Extract content of {braced arg} starting at pos. Returns (content, end_pos)."""
    # skip whitespace
    while pos < len(text) and text[pos] in ' \t\n':
        pos += 1
    if pos >= len(text) or text[pos] != '{':
        return '', pos
    depth, start = 1, pos + 1
    pos = start
    while pos < len(text) and depth:
        if text[pos] == '{':
            depth += 1
        elif text[pos] == '}':
            depth -= 1
        pos += 1
    return text[start:pos - 1], pos


def skip_opt(text, pos):
    """Skip optional [...] arg. Returns end_pos."""
    while pos < len(text) and text[pos] in ' \t\n':
        pos += 1
    if pos < len(text) and text[pos] == '[':
        depth = 1
        pos += 1
        while pos < len(text) and depth:
            if text[pos] == '[':
                depth += 1
            elif text[pos] == ']':
                depth -= 1
            pos += 1
    return pos


def extract_frames(tex):
    """Yield dicts {title, content} for every \\begin{frame}...\\end{frame}."""
    pattern = re.compile(r'\\begin\{frame\}')
    end_pat = re.compile(r'\\(?:begin|end)\{frame\}')
    i = 0
    while True:
        m = pattern.search(tex, i)
        if not m:
            break
        pos = m.end()

        # skip optional args and extract title
        pos = skip_opt(tex, pos)   # e.g. [fragile]
        pos = skip_opt(tex, pos)   # e.g. [T]
        title, pos = extract_arg(tex, pos)
        title = inline(title)

        # find matching \end{frame} tracking nesting
        depth = 1
        search = pos
        frame_body_start = pos
        while depth:
            mm = end_pat.search(tex, search)
            if not mm:
                i = len(tex)
                break
            if 'begin' in mm.group():
                depth += 1
                search = mm.end()
            else:
                depth -= 1
                if depth == 0:
                    yield {'title': title, 'content': tex[frame_body_start:mm.start()]}
                    i = mm.end()
                    break
                search = mm.end()
        else:
            break


# ── Inline LaTeX → text/HTML ─────────────────────────────────────────────────

_SIZE_RE = re.compile(
    r'\\(?:Huge|huge|LARGE|Large|large|normalsize|small|footnotesize|scriptsize|tiny)\s*')
_VSPACE_RE = re.compile(r'\\(?:vfill|hfill|vspace|hspace|vskip|medskip|smallskip|bigskip)\*?(?:\{[^}]*\})?\s*')
_INSERT_RE = re.compile(r'\\insert[A-Za-z]+')
_LINEBREAK_RE = re.compile(r'\\\\(?:\[[^\]]*\])?')
_CMD_ARG_RE = re.compile(r'\\[a-zA-Z]+\*?\{([^{}]*)\}')
_CMD_RE = re.compile(r'\\[a-zA-Z]+\*?')


def fa_replace(text):
    for cmd, emoji in FA.items():
        text = text.replace(f'\\{cmd}', emoji)
    # any remaining \faXxx → generic icon
    text = re.sub(r'\\fa[A-Z][A-Za-z]*', '◆', text)
    return text


def inline(text):
    """Convert inline LaTeX to plain-ish text."""
    text = fa_replace(text)
    text = _SIZE_RE.sub('', text)
    text = _VSPACE_RE.sub(' ', text)
    text = _INSERT_RE.sub('', text)
    text = re.sub(r'\\textbf\{([^{}]*)\}', r'**\1**', text)
    text = re.sub(r'\\(?:textit|emph)\{([^{}]*)\}', r'*\1*', text)
    text = re.sub(r'\\textcolor\{[^}]*\}\{([^{}]*)\}', r'\1', text)
    text = re.sub(r'\\(?:textrm|texttt|textsf|textsc|textup|textsl|text)\{([^{}]*)\}', r'\1', text)
    text = _LINEBREAK_RE.sub(' ', text)
    text = re.sub(r'\\(?:centering|noindent|par)\b\s*', '', text)
    text = _CMD_ARG_RE.sub(r'\1', text)   # \cmd{arg} → arg
    text = _CMD_RE.sub('', text)           # remaining \cmd → ''
    text = text.replace('{', '').replace('}', '')
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


# ── Block conversion ──────────────────────────────────────────────────────────

def convert_itemize(body, ordered=False):
    items = re.split(r'\\item\b', body)
    tag = 'ol' if ordered else 'ul'
    li = ''.join(f'<li>{inline(it.strip())}</li>' for it in items[1:] if it.strip())
    return f'<{tag}>{li}</{tag}>'


def convert_columns(body):
    cols = re.findall(r'\\begin\{column\}[^}]*\}(.*?)\\end\{column\}', body, re.DOTALL)
    inner = ''.join(f'<div class="column" style="flex:1">{convert_body(c)}</div>' for c in cols)
    return f'<div style="display:flex;gap:1em">{inner}</div>'


def convert_block_env(title, body):
    return (f'<div style="background:rgba(255,255,255,.1);border-left:4px solid #e94560;'
            f'padding:.5em 1em;margin:.5em 0">'
            f'<strong>{inline(title)}</strong><br>{inline(body)}</div>')


def convert_body(text):
    """Convert a frame body (or column body) to HTML."""
    # Strip comments
    text = re.sub(r'%[^\n]*', '', text)

    # itemize / enumerate
    text = re.sub(r'\\begin\{itemize\}(.*?)\\end\{itemize\}',
                  lambda m: convert_itemize(m.group(1)), text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{enumerate\}(.*?)\\end\{enumerate\}',
                  lambda m: convert_itemize(m.group(1), ordered=True), text, flags=re.DOTALL)

    # columns
    text = re.sub(r'\\begin\{columns\}[^\n]*(.*?)\\end\{columns\}',
                  lambda m: convert_columns(m.group(1)), text, flags=re.DOTALL)

    # center
    text = re.sub(r'\\begin\{center\}(.*?)\\end\{center\}',
                  lambda m: f'<div style="text-align:center">{inline(m.group(1))}</div>',
                  text, flags=re.DOTALL)

    # block / alertblock / exampleblock
    text = re.sub(
        r'\\begin\{(?:block|alertblock|exampleblock)\}\{([^}]*)\}(.*?)\\end\{(?:block|alertblock|exampleblock)\}',
        lambda m: convert_block_env(m.group(1), m.group(2)), text, flags=re.DOTALL)

    # drop remaining environments we don't handle (just keep content)
    text = re.sub(r'\\begin\{[^}]+\}[^\n]*', '', text)
    text = re.sub(r'\\end\{[^}]+\}', '', text)

    # inline pass on remainder
    text = inline(text)

    # collapse blank lines
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    tex = Path(args.input).read_text(encoding='utf-8', errors='replace')
    frames = list(extract_frames(tex))
    print(f'[tex_extract] {len(frames)} frames found', file=sys.stderr)

    lines = []
    for idx, f in enumerate(frames):
        title = f['title'] or f'Slide {idx + 1}'
        body  = convert_body(f['content'])
        lines += [f'## {title}', '', body, '', '']

    Path(args.output).write_text('\n'.join(lines), encoding='utf-8')
    print(f'[tex_extract] → {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()
