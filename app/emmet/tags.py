"""Tag/rule structure helpers behind Emmet's editor actions (pure functions on text)."""
import re
from dataclasses import dataclass

from .common import Edit
from .markup_data import VOID_ELEMENTS

_TOKEN_RE = re.compile(
    r"(?P<comment><!--.*?-->)"
    r"|(?P<cdata><!\[CDATA\[.*?\]\]>)"
    r"|(?P<decl><![^>]*>)"
    r"|(?P<pi><\?.*?\?>)"
    r"|<(?P<close>/)?(?P<name>[A-Za-z][\w:.-]*)"
    r"(?P<attrs>(?:\"[^\"]*\"|'[^']*'|[^'\">])*?)(?P<selfclose>/)?>",
    re.S,
)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def select(a, b):
    """An Edit that changes nothing and just selects a..b."""
    return Edit(a, a, "", a, b)


@dataclass
class Element:
    name: str
    open_start: int
    open_end: int
    close_start: int | None
    close_end: int | None
    self_closing: bool
    parent: "Element | None" = None

    @property
    def end(self):
        return self.close_end if self.close_end is not None else self.open_end

    @property
    def paired(self):
        return self.close_start is not None

    @property
    def is_void(self):
        return self.self_closing or self.name.lower() in VOID_ELEMENTS


def scan(text):
    """All elements in document order, with their opening/closing tag positions."""
    elements = []
    stack = []
    pos = 0
    while True:
        m = _TOKEN_RE.search(text, pos)
        if not m:
            break
        pos = m.end()
        name = m.group("name")
        if name is None:
            continue
        lname = name.lower()
        if m.group("close"):
            for idx in range(len(stack) - 1, -1, -1):
                if stack[idx].name.lower() == lname:
                    el = stack[idx]
                    el.close_start, el.close_end = m.start(), m.end()
                    del stack[idx:]
                    break
            continue
        el = Element(name, m.start(), m.end(), None, None, bool(m.group("selfclose")),
                     stack[-1] if stack else None)
        elements.append(el)
        if el.self_closing or lname in VOID_ELEMENTS:
            continue
        if lname in ("script", "style"):
            cm = re.compile(rf"</{lname}\s*>", re.I).search(text, pos)
            if cm:
                el.close_start, el.close_end = cm.start(), cm.end()
                pos = cm.end()
            else:
                pos = len(text)
            continue
        stack.append(el)
    return elements


def enclosing(elements, pos):
    best = None
    for el in elements:
        if el.open_start <= pos <= el.end:
            if best is None or (el.end - el.open_start) < (best.end - best.open_start):
                best = el
    return best


def _line_bounds(text, pos):
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return start, len(text) if end == -1 else end


def _indent_of(text, pos):
    start, _ = _line_bounds(text, pos)
    m = re.match(r"[ \t]*", text[start:])
    return m.group(0)


# --------------------------------------------------------------------- balance

def _html_ranges(text):
    out = []
    for el in scan(text):
        out.append((el.open_start, el.end))
        if el.paired and el.open_end < el.close_start:
            out.append((el.open_end, el.close_start))
    return out


def css_ranges(text):
    """Rules (with selector), rule bodies, declarations and values, as (start, end) ranges."""
    out = []
    stack = []
    seg = 0
    i = 0
    n = len(text)

    def strip_range(a, b):
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        return a, b

    def add_declaration(a, b, semicolon_end):
        a, b2 = strip_range(a, b)
        if a >= b2 or ":" not in text[a:b2]:
            return
        out.append((a, semicolon_end))
        colon = text.index(":", a)
        va, vb = strip_range(colon + 1, b2)
        if va < vb:
            out.append((va, vb))

    while i < n:
        c = text[i]
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if not text[seg:i].strip():
                seg = n if end == -1 else end + 2
            i = n if end == -1 else end + 2
            continue
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if c == "{":
            a, _ = strip_range(seg, i)
            stack.append((a, i))
            seg = i + 1
        elif c == "}":
            if stack:
                add_declaration(seg, i, i)
                head, open_i = stack.pop()
                out.append((open_i + 1, i))
                out.append((head, i + 1))
            seg = i + 1
        elif c == ";":
            if stack:
                add_declaration(seg, i, i + 1)
            seg = i + 1
        i += 1
    return out


def _ranges_for(text, language):
    return css_ranges(text) if language in ("css", "sass", "stylus") else _html_ranges(text)


def balance_outward(text, s, e, language="html"):
    best = None
    for a, b in _ranges_for(text, language):
        if a <= s and e <= b and (a, b) != (s, e):
            if best is None or (b - a) < (best[1] - best[0]):
                best = (a, b)
    return select(*best) if best else None


def balance_inward(text, s, e, language="html"):
    if s == e:
        return balance_outward(text, s, e, language)
    best = None
    for a, b in _ranges_for(text, language):
        if s <= a and b <= e and (a, b) != (s, e):
            if best is None or (b - a) > (best[1] - best[0]):
                best = (a, b)
    return select(*best) if best else None


# --------------------------------------------------------------- matching pair

def go_to_matching_pair(text, pos, language="html"):
    if language in ("css", "sass", "stylus", "javascript", "jsx", "json", "python"):
        return _match_bracket(text, pos)
    elements = scan(text)
    el = enclosing(elements, pos)
    if el is None:
        return None
    if el.open_start <= pos <= el.open_end and el.paired:
        return select(el.close_start, el.close_start)
    if el.paired and el.close_start <= pos <= el.close_end:
        return select(el.open_start, el.open_start)
    return select(el.open_start, el.open_start)


def _match_bracket(text, pos):
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = {v: k for k, v in pairs.items()}
    for p in (pos, pos - 1):
        if 0 <= p < len(text):
            c = text[p]
            if c in pairs:
                depth = 0
                for i in range(p, len(text)):
                    if text[i] == c:
                        depth += 1
                    elif text[i] == pairs[c]:
                        depth -= 1
                        if depth == 0:
                            return select(i, i)
                return None
            if c in closers:
                depth = 0
                for i in range(p, -1, -1):
                    if text[i] == c:
                        depth += 1
                    elif text[i] == closers[c]:
                        depth -= 1
                        if depth == 0:
                            return select(i, i)
                return None
    return None


# ------------------------------------------------------------------ tag edits

def _target_element(text, s, e):
    elements = scan(text)
    if s != e:
        for el in elements:
            if el.open_start == s and el.end == e:
                return el
    return enclosing(elements, s)


def _dedent_inner(inner, unit="    "):
    lines = inner.split("\n")
    if len(lines) == 1:
        return inner.strip()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    out = []
    for line in lines:
        if line.startswith(unit):
            line = line[len(unit):]
        elif line.startswith("\t"):
            line = line[1:]
        out.append(line)
    if out:
        out[0] = out[0].lstrip()
    return "\n".join(out)


def remove_tag(text, pos):
    el = enclosing(scan(text), pos)
    if el is None:
        return None
    if not el.paired:
        start, end = el.open_start, el.end
        return Edit(start, end, "", start, start)
    inner = text[el.open_end:el.close_start]
    replacement = _dedent_inner(inner)
    return Edit(el.open_start, el.end, replacement, el.open_start, el.open_start + len(replacement))


def split_join_tag(text, pos):
    el = enclosing(scan(text), pos)
    if el is None:
        return None
    open_text = text[el.open_start:el.open_end]
    if el.self_closing and not el.paired:
        head = open_text[:-2].rstrip()
        new = f"{head}></{el.name}>"
        return Edit(el.open_start, el.open_end, new, el.open_start, el.open_start + len(new))
    if el.paired and not text[el.open_end:el.close_start].strip():
        head = open_text[:-1].rstrip()
        new = head + "/>"
        return Edit(el.open_start, el.end, new, el.open_start, el.open_start + len(new))
    return None


def merge_lines(text, s, e):
    if s == e:
        el = enclosing(scan(text), s)
        if el is not None and "\n" in text[el.open_start:el.end]:
            s, e = el.open_start, el.end
        else:
            ls, le = _line_bounds(text, s)
            nxt = text.find("\n", le + 1)
            if le >= len(text):
                return None
            s, e = ls, len(text) if nxt == -1 else nxt
    else:
        s = text.rfind("\n", 0, s) + 1
        end_nl = text.find("\n", e)
        e = len(text) if end_nl == -1 else end_nl
    lines = [l.strip() for l in text[s:e].split("\n") if l.strip()]
    if len(lines) < 2:
        return None
    merged = lines[0]
    for line in lines[1:]:
        if merged.endswith(">") or line.startswith("<"):
            merged += line
        else:
            merged += " " + line
    indent = re.match(r"[ 	]*", text[s:e]).group(0)
    return Edit(s, e, indent + merged, s, s + len(indent) + len(merged))


# ------------------------------------------------------------ select item / points

_OPEN_TAG_RE = re.compile(r"<([A-Za-z][\w:.-]*)((?:\"[^\"]*\"|'[^']*'|[^'\">])*)>", re.S)
_ATTR_RE = re.compile(r"""([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?""")


def html_items(text):
    items = []
    for m in _OPEN_TAG_RE.finditer(text):
        name_start = m.start(1)
        items.append((name_start, m.end(1)))
        attrs_start = m.start(2)
        for am in _ATTR_RE.finditer(m.group(2)):
            a = attrs_start + am.start()
            b = attrs_start + am.end()
            items.append((a, b))
            for grp in (2, 3, 4):
                if am.group(grp) is not None:
                    va = attrs_start + am.start(grp)
                    vb = attrs_start + am.end(grp)
                    if va < vb:
                        items.append((va, vb))
    return sorted(set(items))


def css_items(text):
    items = []
    for a, b in css_ranges(text):
        items.append((a, b))
    for m in re.finditer(r"([A-Za-z-]+)\s*:", text):
        items.append((m.start(1), m.end(1)))
    return sorted(set(items))


def select_item(text, s, e, language, forward=True):
    items = css_items(text) if language in ("css", "sass", "stylus") else html_items(text)
    if forward:
        for a, b in items:
            if a > s:
                return select(a, b)
    else:
        for a, b in reversed(items):
            if a < s:
                return select(a, b)
    return None


def edit_points(text):
    points = set()
    for m in re.finditer(r">(?=<)", text):
        points.add(m.end())
    for m in re.finditer(r"=(\"\"|'')", text):
        points.add(m.start() + 2)
    for m in re.finditer(r"^[ \t]*$", text, re.M):
        points.add(m.end())
    return sorted(points)


def next_edit_point(text, pos, forward=True):
    pts = edit_points(text)
    if forward:
        for p in pts:
            if p > pos:
                return select(p, p)
    else:
        for p in reversed(pts):
            if p < pos:
                return select(p, p)
    return None


# --------------------------------------------------------------------- comments

def toggle_html_comment(text, s, e):
    if s == e:
        for m in _COMMENT_RE.finditer(text):
            if m.start() <= s <= m.end():
                return _uncomment_html(text, m.start(), m.end())
        el = enclosing(scan(text), s)
        if el is not None:
            s, e = el.open_start, el.end
        else:
            s, e = _line_bounds(text, s)
            while s < e and text[s].isspace():
                s += 1
    else:
        for m in _COMMENT_RE.finditer(text):
            if m.start() == s and m.end() == e:
                return _uncomment_html(text, s, e)
    if s >= e:
        return None
    body = text[s:e]
    new = f"<!-- {body} -->"
    return Edit(s, e, new, s, s + len(new))


def _uncomment_html(text, a, b):
    inner = text[a + 4:b - 3]
    if inner.startswith(" "):
        inner = inner[1:]
    if inner.endswith(" "):
        inner = inner[:-1]
    return Edit(a, b, inner, a, a + len(inner))


def toggle_block_comment(text, s, e, language="css"):
    """/* ... */ toggling for CSS: selection, declaration line, or a whole rule."""
    for m in re.finditer(r"/\*.*?\*/", text, re.S):
        if m.start() <= s <= m.end() and (s == e or (m.start() <= s and e <= m.end())):
            inner = text[m.start() + 2:m.end() - 2]
            inner = inner[1:] if inner.startswith(" ") else inner
            inner = inner[:-1] if inner.endswith(" ") else inner
            return Edit(m.start(), m.end(), inner, m.start(), m.start() + len(inner))
    if s == e:
        ls, le = _line_bounds(text, s)
        line = text[ls:le]
        a = ls + (len(line) - len(line.lstrip()))
        b = le - (len(line) - len(line.rstrip()))
        if a >= b:
            return None
        if text[a:b].endswith("{"):
            depth = 0
            for i in range(b - 1, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        b = i + 1
                        break
        s, e = a, b
    body = text[s:e]
    new = f"/* {body} */"
    return Edit(s, e, new, s, s + len(new))
