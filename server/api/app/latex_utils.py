from __future__ import annotations

import re

from pylatexenc.latex2text import LatexNodes2Text

_DEF_RE = re.compile(r"\\(?:newcommand|renewcommand)\*?\s*")
_HREF_RE = re.compile(r"\\href\*?\s*\{")


def _read_group(text: str, pos: int) -> tuple[str, int]:
    """text[pos] must be '{'. Returns (content, index just past the matching '}')."""
    depth = 0
    i = pos
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[pos + 1 : i], i + 1
        i += 1
    raise ValueError("unbalanced braces")


def _skip_ws(text: str, pos: int) -> int:
    while pos < len(text) and text[pos] in " \t\r\n":
        pos += 1
    return pos


def _expand_user_macros(tex: str, max_passes: int = 8) -> str:
    """Textually expand \\newcommand/\\renewcommand macros before handing off to
    pylatexenc, which never expands macros itself. Templates that split a single
    environment across two paired macros (e.g. Jake's-resume-style
    \\resumeSubHeadingListStart/\\...End wrapping \\begin{itemize}/\\end{itemize})
    parse fine once expanded in place, but produce an unclosed-environment error
    if pylatexenc encounters the \\newcommand bodies as standalone literal text.
    """
    macros: dict[str, tuple[int, str]] = {}
    spans: list[tuple[int, int]] = []
    for m in _DEF_RE.finditer(tex):
        pos = _skip_ws(tex, m.end())
        if pos >= len(tex) or tex[pos] != "{":
            continue
        name_group, pos = _read_group(tex, pos)
        name = name_group.strip().lstrip("\\")
        pos = _skip_ws(tex, pos)
        nargs = 0
        if pos < len(tex) and tex[pos] == "[":
            end = tex.index("]", pos)
            nargs = int(tex[pos + 1 : end])
            pos = _skip_ws(tex, end + 1)
            if pos < len(tex) and tex[pos] == "[":  # default-value for #1, unused here
                pos = _skip_ws(tex, tex.index("]", pos) + 1)
        if pos >= len(tex) or tex[pos] != "{":
            continue
        body, end_pos = _read_group(tex, pos)
        macros[name] = (nargs, body)
        spans.append((m.start(), end_pos))

    if not macros:
        return tex

    out_parts = []
    last = 0
    for start, end in spans:
        out_parts.append(tex[last:start])
        last = end
    out_parts.append(tex[last:])
    body_text = "".join(out_parts)

    macro_name_re = re.compile(r"\\([a-zA-Z]+)")
    for _pass in range(max_passes):
        changed = False
        out = []
        i = 0
        while i < len(body_text):
            c = body_text[i]
            if c == "\\":
                name_match = macro_name_re.match(body_text[i:])
                if name_match and name_match.group(1) in macros:
                    name = name_match.group(1)
                    nargs, mbody = macros[name]
                    j = _skip_ws(body_text, i + name_match.end())
                    args = []
                    ok = True
                    for _a in range(nargs):
                        j = _skip_ws(body_text, j)
                        if j < len(body_text) and body_text[j] == "{":
                            g, j = _read_group(body_text, j)
                            args.append(g)
                        else:
                            ok = False
                            break
                    if ok:
                        expansion = mbody
                        for k, a in enumerate(args, start=1):
                            expansion = expansion.replace(f"#{k}", a)
                        out.append(expansion)
                        i = j
                        changed = True
                        continue
            out.append(c)
            i += 1
        body_text = "".join(out)
        if not changed:
            break
    return body_text


def _strip_hrefs(tex: str) -> str:
    """Replace \\href{url}{text} with just `text`.

    Works around a crash in pylatexenc 2.10's built-in \\href handler
    (IndexError on nodeargd.argnlist) and keeps raw URLs out of the
    plaintext used for keyword/embedding matching.
    """
    out = []
    i = 0
    for m in _HREF_RE.finditer(tex):
        if m.start() < i:
            continue
        out.append(tex[i : m.start()])
        pos = m.end() - 1  # position of the opening '{'
        _url, pos = _read_group(tex, pos)
        pos = _skip_ws(tex, pos)
        if pos < len(tex) and tex[pos] == "{":
            text, pos = _read_group(tex, pos)
        else:
            text = ""
        out.append(text)
        i = pos
    out.append(tex[i:])
    return "".join(out)


def tex_to_plaintext(tex: str) -> str:
    expanded = _expand_user_macros(tex)
    expanded = _strip_hrefs(expanded)
    return LatexNodes2Text().latex_to_text(expanded).strip()
