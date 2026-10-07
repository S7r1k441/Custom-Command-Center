"""Emmet CSS abbreviations (also SCSS, Less, Sass and Stylus output styles)."""
import re

from . import stylesheet_data as S
from .common import Expansion

CSS_SYNTAXES = {"css", "sass", "stylus"}

_NUM_RE = re.compile(r"-?(?:\d*\.\d+|\d+)([a-z%]*)")
_COLOR_RE = re.compile(r"#([0-9a-fA-F]+)(?:\.(\d+))?")
_KW_RE = re.compile(r"[a-z]+")
_PREFIX_RE = re.compile(r"([wmso]+)-")
_PROPERTY_SET = set(S.PROPERTIES)
_NAMED_COLORS = {
    "red", "blue", "green", "black", "white", "gray", "grey", "orange", "yellow", "purple",
    "pink", "brown", "transparent", "currentcolor", "navy", "teal", "silver", "gold", "cyan",
}
_COLOR_PROPS = {"color", "background-color", "border-color", "outline-color", "background",
                "border", "fill", "stroke", "caret-color", "text-decoration-color"}


class _Stop:
    __slots__ = ("default",)

    def __init__(self, default=""):
        self.default = default


# --------------------------------------------------------------- value parts

def _hex_color(digits, alpha):
    if len(digits) == 1:
        full = digits * 3
    elif len(digits) == 2:
        full = digits * 3
    elif len(digits) == 3:
        full = digits
    elif len(digits) == 6:
        full = digits
    else:
        return None
    if alpha is None:
        return "#" + full
    if len(full) == 3:
        full = "".join(c * 2 for c in full)
    r, g, b = (int(full[i:i + 2], 16) for i in (0, 2, 4))
    a = "0." + alpha if not alpha.startswith("0") and len(alpha) else alpha
    return f"rgba({r}, {g}, {b}, {a})"


def _number(match, prop):
    text = match.group(0)
    unit = match.group(1)
    num = text[: len(text) - len(unit)]
    if unit:
        unit = S.UNIT_ALIASES.get(unit, unit)
        if unit not in S.UNITS:
            return None
        return num + unit
    try:
        is_zero = float(num) == 0
    except ValueError:
        return None
    if is_zero or prop in S.UNITLESS:
        return num
    return num + "px"


def _keyword(token, prop):
    words = (S.KEYWORDS.get(prop, "") + " " + S._GLOBAL_KEYWORDS).split()
    if token in words:
        return token
    for w in words:
        if w.startswith(token):
            return w
    for w in words:
        if w[0] == token[0] and _is_subsequence(token, w):
            return w
    if token in _NAMED_COLORS and (prop in _COLOR_PROPS or prop.endswith("color")):
        return token
    return None


def _is_subsequence(needle, hay):
    it = iter(hay)
    return all(ch in it for ch in needle)


def _parse_value(rest, prop):
    """Turn the value part of an abbreviation into CSS. '' means no value; None means invalid."""
    if rest == "":
        return ""
    if rest[0] == ":":
        rest = rest[1:]
        if rest == "":
            return ""
    if "(" in rest and rest.endswith(")"):
        return rest
    if re.fullmatch(r"[a-z-]+", rest):
        kw = _keyword(rest, prop)
        if kw:
            return kw
        if "-" not in rest:
            return None
    tokens = []
    i = 0
    expect = True
    while i < len(rest):
        c = rest[i]
        if c == "-" and not expect:
            i += 1
            expect = True
            continue
        m = _NUM_RE.match(rest, i)
        if m:
            value = _number(m, prop)
            if value is None:
                return None
            tokens.append(value)
            i = m.end()
            expect = False
            continue
        if c == "-":
            i += 1
            continue
        m = _COLOR_RE.match(rest, i)
        if m:
            color = _hex_color(m.group(1), m.group(2))
            if color is None:
                return None
            tokens.append(color)
            i = m.end()
            expect = False
            continue
        m = _KW_RE.match(rest, i)
        if m:
            kw = _keyword(m.group(0), prop)
            if kw is None:
                return None
            tokens.append(kw)
            i = m.end()
            expect = False
            continue
        return None
    if expect or not tokens:
        return None
    return " ".join(tokens)


# ------------------------------------------------------------ property lookup

def _fuzzy_property(head):
    if len(head) < 2 or not head.isalpha():
        return None
    best, best_score = None, 0.0
    for name in S.PROPERTIES:
        if name[0] != head[0] or not _is_subsequence(head, name):
            continue
        pos = 0
        score = 0.0
        ok = True
        for ch in head:
            starts = [m for m in range(pos, len(name)) if name[m] == ch and (m == 0 or name[m - 1] == "-")]
            if starts:
                idx = starts[0]
                score += 3
            else:
                idx = name.find(ch, pos)
                if idx < 0:
                    ok = False
                    break
                score += 1
            pos = idx + 1
        if not ok:
            continue
        score -= len(name) * 0.01
        if score > best_score:
            best, best_score = name, score
    return best


def _explicit_property(head):
    if head in S.SNIPPETS:
        return S.SNIPPETS[head][0]
    if head in _PROPERTY_SET:
        return head
    return None


def _find_declaration(p):
    """Return (property, value) for an abbreviation like 'm10-20' or 'pos:a'."""
    if ":" in p and "(" not in p.split(":", 1)[0]:
        head, _, value = p.partition(":")
        prop = _explicit_property(head) or _fuzzy_property(head)
        if prop is None:
            return None
        parsed = _parse_value(value, prop)
        return (prop, parsed) if parsed is not None else None
    for finder in (_explicit_property, _fuzzy_property):
        for k in range(len(p), 0, -1):
            head, rest = p[:k], p[k:]
            prop = finder(head)
            if prop is None:
                continue
            parsed = _parse_value(rest, prop)
            if parsed is not None:
                return prop, parsed
    return None


# ------------------------------------------------------------------ assembly

def _default_for(head_abbr, prop):
    if head_abbr in S.SNIPPETS and S.SNIPPETS[head_abbr][0] == prop and S.SNIPPETS[head_abbr][1]:
        return S.SNIPPETS[head_abbr][1]
    return S.DEFAULT_VALUES.get(prop, "")


def _split_plus(abbr):
    parts, depth, cur = [], 0, []
    for ch in abbr:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "+" and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def _gradient(p):
    m = re.fullmatch(r"(lg|rg)\((.*)\)", p)
    if not m:
        return None
    func = "linear-gradient" if m.group(1) == "lg" else "radial-gradient"
    args = []
    for raw in m.group(2).split(","):
        words = []
        for word in raw.strip().split():
            cm = _COLOR_RE.fullmatch(word)
            if cm:
                word = _hex_color(cm.group(1), cm.group(2)) or word
            words.append(word)
        args.append(" ".join(words))
    return "background-image", f"{func}({', '.join(args)})"


def _declaration_lines(p, syntax):
    important = p.endswith("!")
    if important:
        p = p[:-1]
    prefixes = ""
    if p.startswith("-"):
        rest = p[1:]
        m = _PREFIX_RE.match(rest)
        if m:
            prefixes, p = m.group(1), rest[m.end():]
        else:
            prefixes, p = "wmso", rest
    found = _gradient(p)
    if found is None:
        found = _find_declaration(p)
    if found is None:
        return None
    prop, value = found
    head_abbr = re.match(r"[a-z]+", p).group(0) if re.match(r"[a-z]+", p) else ""
    lines = []
    names = [S.PREFIXES[c] + prop for c in "wmso" if c in prefixes] + [prop]
    for idx, name in enumerate(names):
        last = idx == len(names) - 1
        if value:
            val_parts = [value]
        else:
            default = _default_for(head_abbr, prop)
            val_parts = [_Stop(default)] if last else [default]
        if important:
            val_parts.append(" !important")
        if syntax == "stylus":
            line = [name + " "] + val_parts
        elif syntax == "sass":
            line = [name + ": "] + val_parts
        else:
            line = [name + ": "] + val_parts + [";"]
        lines.append(line)
    return lines


_PLACEHOLDER_RE = re.compile(r"\$\{(\d+)(?::([^}]*))?\}")


def _from_template(template, indent):
    template = template.replace("{P}", indent)
    parts = []
    pos = 0
    for m in _PLACEHOLDER_RE.finditer(template):
        parts.append(template[pos:m.start()])
        parts.append(_Stop(m.group(2) or ""))
        pos = m.end()
    parts.append(template[pos:])
    return parts


_AT_RULES = {
    "@i": "@import url(${1});",
    "@import": "@import url(${1});",
    "@m": "@media ${1:screen} {\n{P}${2}\n}",
    "@media": "@media ${1:screen} {\n{P}${2}\n}",
    "@f": "@font-face {\n{P}font-family: ${1};\n{P}src: url(${2});\n}",
    "@font-face": "@font-face {\n{P}font-family: ${1};\n{P}src: url(${2});\n}",
    "@kf": "@keyframes ${1:identifier} {\n{P}from { ${2} }\n{P}to { ${3} }\n}",
    "@keyframes": "@keyframes ${1:identifier} {\n{P}from { ${2} }\n{P}to { ${3} }\n}",
    "@c": '@charset "UTF-8";',
    "@charset": '@charset "UTF-8";',
    "@s": "@supports (${1:display: grid}) {\n{P}${2}\n}",
    "@supports": "@supports (${1:display: grid}) {\n{P}${2}\n}",
    "@p": "@page {\n{P}${1}\n}",
    "@page": "@page {\n{P}${1}\n}",
}


def _finalize(parts):
    text, stops, length = [], [], 0
    for p in parts:
        if isinstance(p, _Stop):
            stops.append((length, length + len(p.default)))
            text.append(p.default)
            length += len(p.default)
        else:
            text.append(p)
            length += len(p)
    return Expansion("".join(text), stops)


def expand(abbr, syntax="css", indent="    "):
    """Expand a CSS abbreviation. Returns an Expansion, or None if it isn't valid."""
    abbr = abbr.strip()
    if not abbr:
        return None
    if abbr.startswith("@"):
        template = _AT_RULES.get(abbr)
        return _finalize(_from_template(template, indent)) if template else None
    if abbr == "!":
        return Expansion("!important", [])
    parts = []
    for i, chunk in enumerate(_split_plus(abbr)):
        lines = _declaration_lines(chunk, syntax)
        if lines is None:
            return None
        for line in lines:
            if parts:
                parts.append("\n")
            parts.extend(line)
    return _finalize(parts)
