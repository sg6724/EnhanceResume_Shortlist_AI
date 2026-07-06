from __future__ import annotations

from pylatexenc.latex2text import LatexNodes2Text


def tex_to_plaintext(tex: str) -> str:
    return LatexNodes2Text().latex_to_text(tex).strip()
