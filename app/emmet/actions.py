"""Emmet editor actions that work on plain text: math, number stepping, comments, images."""
import base64
import mimetypes
import re

from .common import Edit
from .tags import (_line_bounds, scan, select, toggle_block_comment, toggle_html_comment)

# ----------------------------------------------------------------------- math

_MATH_CHARS = set("0123456789.+-*/\\()%")


class _MathError(Exception):
    pass


def _evaluate(expr):
    tokens = re.findall(r"\d*\.\d+|\d+|[-+*/\\%()]", expr.replace(" ", ""))
    if "".join(tokens) != expr.replace(" ", ""):
        raise _MathError
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def parse_expr():
        nonlocal pos
        value = parse_term()
        while peek() in ("+", "-"):
            op = tokens[pos]
            pos += 1
            rhs = parse_term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def parse_term():
        nonlocal pos
        value = parse_factor()
        while peek() in ("*", "/", "\\", "%"):
            op = tokens[pos]
            pos += 1
            rhs = parse_factor()
            if op == "*":
                value *= rhs
            elif rhs == 0:
                raise _MathError
            elif op == "/":
                value /= rhs
            elif op == "\\":
                value = float(int(value // rhs))
            else:
                value %= rhs
        return value

    def parse_factor():
        nonlocal pos
        tok = peek()
        if tok in ("-", "+"):
            pos += 1
            v = parse_factor()
            return -v if tok == "-" else v
        if tok == "(":
            pos += 1
            v = parse_expr()
            if peek() != ")":
                raise _MathError
            pos += 1
            return v
        if tok is None or not re.fullmatch(r"\d*\.\d+|\d+", tok):
            raise _MathError
        pos += 1
        return float(tok)

    result = parse_expr()
    if pos != len(tokens):
        raise _MathError
    return result


def _format_number(value):
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def evaluate_math(text, s, e):
    if s == e:
        start = s
        while start > 0 and text[start - 1] in _MATH_CHARS:
            start -= 1
        while start < s and text[start] in "*/+\\%":
            start += 1
        if start < s and text[start] == "-" and start > 0 and (text[start - 1].isalnum() or text[start - 1] in ")_"):
            start += 1
        s_range = (start, s)
    else:
        s_range = (s, e)
    expr = text[s_range[0]:s_range[1]]
    if not expr.strip():
        return None
    try:
        result = _format_number(_evaluate(expr))
    except (_MathError, ValueError, ZeroDivisionError):
        return None
    a = s_range[0]
    return Edit(a, s_range[1], result, a, a + len(result))


# ------------------------------------------------------------ number stepping

_NUMBER_RE = re.compile(r"-?\d*\.?\d+")


def step_number(text, s, e, delta):
    ls, le = _line_bounds(text, s)
    line = text[ls:le]
    col = s - ls
    chosen = None
    for m in _NUMBER_RE.finditer(line):
        a, b = m.start(), m.end()
        if line[a] == "-" and a > 0 and (line[a - 1].isalnum() or line[a - 1] in ")_"):
            a += 1
        if a <= col <= b:
            chosen = (a, b)
            break
    if chosen is None:
        return None
    a, b = chosen
    original = line[a:b]
    decimals = len(original.split(".")[1]) if "." in original else 0
    if delta != int(delta):
        decimals = max(decimals, 1)
    value = round(float(original) + delta, decimals)
    new = f"{value:.{decimals}f}" if decimals else str(int(round(value)))
    start = ls + a
    return Edit(start, ls + b, new, start, start + len(new))


# ------------------------------------------------------------------ comments

LINE_COMMENT = {"python": "#", "javascript": "//", "jsx": "//", "sass": "//", "stylus": "//",
                "pug": "//", "slim": "/", "haml": "-#"}


def toggle_comment(text, s, e, language):
    if language in ("html", "xml", "xsl", "markdown"):
        return toggle_html_comment(text, s, e)
    if language == "css":
        return toggle_block_comment(text, s, e)
    marker = LINE_COMMENT.get(language)
    if marker is None:
        return None
    first = text.rfind("\n", 0, s) + 1
    end_nl = text.find("\n", max(e - (1 if e > s and text[e - 1] == "\n" else 0), s))
    last = len(text) if end_nl == -1 else end_nl
    lines = text[first:last].split("\n")
    body = [l for l in lines if l.strip()]
    if not body:
        return None
    all_commented = all(l.lstrip().startswith(marker) for l in body)
    indent = min(len(l) - len(l.lstrip()) for l in body)
    out = []
    for line in lines:
        if not line.strip():
            out.append(line)
        elif all_commented:
            lead = len(line) - len(line.lstrip())
            rest = line[lead:][len(marker):]
            rest = rest[1:] if rest.startswith(" ") else rest
            out.append(line[:lead] + rest)
        else:
            out.append(line[:indent] + marker + " " + line[indent:])
    new = "\n".join(out)
    return Edit(first, last, new, first, first + len(new))


# --------------------------------------------------------------------- images

_ATTR_TEMPLATE = r"""\s+{name}\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'>/]+)"""


def _attr_value(tag_text, name):
    m = re.search(rf"""\s{name}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>/]+))""", tag_text, re.I)
    if not m:
        return None
    return next(g for g in m.groups() if g is not None)


def update_image_size(text, pos, get_size):
    """Set width/height on the <img> at pos from the image file's real size."""
    for el in scan(text):
        if el.name.lower() == "img" and el.open_start <= pos <= el.open_end:
            tag = text[el.open_start:el.open_end]
            src = _attr_value(tag, "src")
            size = get_size(src) if src else None
            if not size:
                return None
            w, h = size
            tag = re.sub(_ATTR_TEMPLATE.format(name="width"), "", tag, flags=re.I)
            tag = re.sub(_ATTR_TEMPLATE.format(name="height"), "", tag, flags=re.I)
            closing = "/>" if tag.endswith("/>") else ">"
            head = tag[: -len(closing)].rstrip()
            new = f'{head} width="{w}" height="{h}"{closing}'
            return Edit(el.open_start, el.open_end, new, el.open_start, el.open_start + len(new))
    return None


def encode_image(text, pos, read_file):
    """Replace an <img src> or CSS url() with a base64 data: URL."""
    targets = []
    for el in scan(text):
        if el.name.lower() == "img" and el.open_start <= pos <= el.open_end:
            tag = text[el.open_start:el.open_end]
            m = re.search(r"""\ssrc\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>/]+))""", tag, re.I)
            if m:
                for gi in (1, 2, 3):
                    if m.group(gi) is not None:
                        targets.append((el.open_start + m.start(gi), el.open_start + m.end(gi), m.group(gi)))
                        break
    if not targets:
        ls, le = _line_bounds(text, pos)
        for m in re.finditer(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", text[ls:le]):
            if ls + m.start() <= pos <= ls + m.end():
                targets.append((ls + m.start(2), ls + m.end(2), m.group(2)))
    if not targets:
        return None
    a, b, src = targets[0]
    if src.startswith("data:"):
        return None
    loaded = read_file(src)
    if not loaded:
        return None
    mime, data = loaded
    url = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    return Edit(a, b, url, a, a + len(url))


def guess_mime(path):
    return mimetypes.guess_type(path)[0] or "application/octet-stream"
