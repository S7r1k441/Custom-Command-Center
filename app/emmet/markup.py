"""Emmet markup abbreviations: HTML, XML, XSL, JSX, Pug, HAML and Slim."""
import html as _html
import random
import re

from . import markup_data as D
from .common import EmmetError, Expansion

MARKUP_SYNTAXES = {"html", "xml", "xsl", "jsx", "pug", "haml", "slim"}


# --------------------------------------------------------------------- tree

class Attr:
    __slots__ = ("name", "value", "boolean", "excluded")

    def __init__(self, name, value=None, boolean=False, excluded=False):
        self.name = name
        self.value = value
        self.boolean = boolean
        self.excluded = excluded

    def copy(self):
        return Attr(self.name, self.value, self.boolean, self.excluded)


class Node:
    def __init__(self, name=None):
        self.name = name
        self.attrs = []
        self.text = None
        self.children = []
        self.parent = None
        self.self_closing = False
        self.reps = []            # [(index, count)] - innermost repeater last
        self.lorem = None         # word count when this is a lorem text node
        self.implicit = False     # unnamed child requested by a trailing ">"
        self.mult_lines = False   # "*" without a count (used when wrapping text)
        self.expando = False      # abbreviation ended with "+"
        self.applied = set()      # snippet keys already applied to this node
        self.wrapped_markup = False  # text is existing markup wrapped by an abbreviation

    def add(self, child):
        child.parent = self
        self.children.append(child)

    def copy(self):
        n = Node(self.name)
        n.attrs = [a.copy() for a in self.attrs]
        n.text = self.text
        n.self_closing = self.self_closing
        n.reps = list(self.reps)
        n.lorem = self.lorem
        n.implicit = self.implicit
        n.mult_lines = self.mult_lines
        n.expando = self.expando
        n.applied = set(self.applied)
        n.wrapped_markup = self.wrapped_markup
        for c in self.children:
            n.add(c.copy())
        return n

    def attr(self, name):
        for a in self.attrs:
            if a.name == name:
                return a
        return None


def _set_attr(node, name, value, boolean=False, excluded=False):
    existing = node.attr(name)
    if existing is None:
        node.attrs.append(Attr(name, value, boolean, excluded))
    elif name == "class" and existing.value and value:
        existing.value = existing.value + " " + value
    else:
        existing.value, existing.boolean, existing.excluded = value, boolean, excluded


def _merge_attrs(base, override):
    out = [a.copy() for a in base]
    for a in override:
        existing = next((x for x in out if x.name == a.name), None)
        if existing is None:
            out.append(a.copy())
        elif a.name == "class" and existing.value and a.value:
            merged = existing.value.split()
            merged += [c for c in a.value.split() if c not in merged]
            existing.value = " ".join(merged)
        else:
            existing.value, existing.boolean, existing.excluded = a.value, a.boolean, a.excluded
    return out


# ------------------------------------------------------------------- parser

_NAME_RE = re.compile(r"!+\w*|[A-Za-z_][\w-]*(?::[\w-]+)*")
_TOKEN_RE = re.compile(r"[\w$@-]+")
_ATTR_NAME_RE = re.compile(r"[^\s=\]]+")
_DIGITS_RE = re.compile(r"\d+")
_LOREM_RE = re.compile(r"(?:lorem|lipsum)(\d*)")


class _Parser:
    def __init__(self, source, expando=False):
        self.s = source
        self.n = len(source)
        self.i = 0
        self.expando = expando

    def parse(self):
        root = self._sequence(top=True)
        if self.i < self.n:
            raise EmmetError(f"unexpected {self.s[self.i]!r}")
        return root

    def _sequence(self, top):
        s = self.s
        root = Node()
        parents = [root]
        last = []
        while self.i < self.n:
            c = s[self.i]
            if c == ")":
                if top:
                    raise EmmetError("unbalanced )")
                break
            if c == ">":
                if not last:
                    raise EmmetError("'>' needs an element before it")
                self.i += 1
                if self.i >= self.n or s[self.i] == ")":
                    for p in last:
                        child = Node()
                        child.implicit = True
                        p.add(child)
                    last = []
                    continue
                parents = last
                continue
            if c == "+":
                self.i += 1
                continue
            if c == "^":
                while self.i < self.n and s[self.i] == "^":
                    parents = _dedupe([p.parent or root for p in parents])
                    self.i += 1
                continue
            template = self._group() if c == "(" else [self._element()]
            mult = self._multiplier()
            count = mult if isinstance(mult, int) else 1
            new_last = []
            for parent in parents:
                for k in range(1, count + 1):
                    for t in template:
                        node = t.copy()
                        if isinstance(mult, int):
                            node.reps.insert(0, (k, count))
                        elif mult == "lines":
                            node.mult_lines = True
                        parent.add(node)
                        new_last.append(node)
            last = new_last
        if top and self.expando:
            for n in last:
                n.expando = True
        return root

    def _group(self):
        self.i += 1
        inner = self._sequence(top=False)
        if self.i >= self.n or self.s[self.i] != ")":
            raise EmmetError("missing )")
        self.i += 1
        return list(inner.children)

    def _multiplier(self):
        if self.i < self.n and self.s[self.i] == "*":
            self.i += 1
            m = _DIGITS_RE.match(self.s, self.i)
            if m:
                self.i = m.end()
                return int(m.group(0))
            return "lines"
        return None

    def _element(self):
        s = self.s
        node = Node()
        m = _NAME_RE.match(s, self.i)
        if m:
            name = m.group(0)
            self.i = m.end()
            lm = _LOREM_RE.fullmatch(name)
            if lm:
                node.lorem = int(lm.group(1)) if lm.group(1) else 30
            else:
                node.name = name
        props = 1 if m else 0
        while self.i < self.n:
            c = s[self.i]
            if c == "#":
                self.i += 1
                _set_attr(node, "id", self._token())
            elif c == ".":
                self.i += 1
                _set_attr(node, "class", self._token())
            elif c == "[":
                self._attrs(node)
            elif c == "{":
                text = self._text()
                node.text = (node.text or "") + text
            elif c == "/":
                node.self_closing = True
                self.i += 1
            else:
                break
            props += 1
        if not props:
            raise EmmetError(f"unexpected {s[self.i:self.i + 1]!r}")
        return node

    def _token(self):
        m = _TOKEN_RE.match(self.s, self.i)
        if not m:
            raise EmmetError("expected a name")
        self.i = m.end()
        return m.group(0)

    def _text(self):
        s = self.s
        i = self.i + 1
        depth = 1
        buf = []
        while i < self.n:
            c = s[i]
            if c == "\\" and i + 1 < self.n and s[i + 1] in "{}":
                buf.append(s[i + 1])
                i += 2
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    self.i = i + 1
                    return "".join(buf)
            buf.append(c)
            i += 1
        raise EmmetError("missing }")

    def _attrs(self, node):
        s = self.s
        self.i += 1
        while True:
            while self.i < self.n and s[self.i].isspace():
                self.i += 1
            if self.i >= self.n:
                raise EmmetError("missing ]")
            if s[self.i] == "]":
                self.i += 1
                return
            m = _ATTR_NAME_RE.match(s, self.i)
            if not m:
                raise EmmetError("bad attribute")
            name = m.group(0)
            self.i = m.end()
            value = None
            if self.i < self.n and s[self.i] == "=":
                self.i += 1
                value = self._attr_value()
            excluded = name.startswith("!")
            if excluded:
                name = name[1:]
            boolean = name.endswith(".") and value is None
            if boolean:
                name = name[:-1]
            _set_attr(node, name, value, boolean, excluded)

    def _attr_value(self):
        s = self.s
        i = self.i
        if i < self.n and s[i] in "\"'":
            quote = s[i]
            j = i + 1
            buf = []
            while j < self.n and s[j] != quote:
                if s[j] == "\\" and j + 1 < self.n:
                    buf.append(s[j + 1])
                    j += 2
                    continue
                buf.append(s[j])
                j += 1
            if j >= self.n:
                raise EmmetError("unterminated quote")
            self.i = j + 1
            return "".join(buf)
        depth = 0
        j = i
        while j < self.n:
            ch = s[j]
            if ch == "$" and j + 1 < self.n and s[j + 1] == "{":
                depth += 1
                j += 2
                continue
            if depth and ch == "}":
                depth -= 1
            elif depth == 0 and (ch.isspace() or ch == "]"):
                break
            j += 1
        self.i = j
        return s[i:j]


def _dedupe(items):
    seen = []
    for x in items:
        if not any(x is y for y in seen):
            seen.append(x)
    return seen


# ------------------------------------------------- snippets & implicit names

class _Ctx:
    def __init__(self, syntax, indent, filters, rng):
        self.syntax = syntax
        self.pad = indent
        self.filters = filters
        self.rng = rng
        self.first_lorem = True
        if syntax == "xsl":
            self.snippets = D.XSL_SNIPPETS
        elif syntax == "xml":
            self.snippets = {}
        else:
            self.snippets = D.HTML_SNIPPETS
        self.inline = set() if syntax in ("xml", "xsl") else D.INLINE_ELEMENTS


def _implicit_name(parent_name, syntax):
    if syntax in ("xml", "xsl"):
        return "div"
    p = (parent_name or "").lower()
    if p in D.IMPLICIT_CHILD:
        return D.IMPLICIT_CHILD[p]
    if p in D.IMPLICIT_SPAN_PARENTS:
        return "span"
    return "div"


def _apply_snippet(node, ctx, depth=0):
    if depth > 8 or node.name is None:
        return
    key = node.name
    snippet = None
    plus = key + "+"
    if node.expando and plus in ctx.snippets and plus not in node.applied:
        snippet, used = ctx.snippets[plus], plus
    elif key in ctx.snippets and key not in node.applied:
        snippet, used = ctx.snippets[key], key
    else:
        return
    node.applied.add(used)
    try:
        frag = _Parser(snippet).parse()
    except EmmetError:
        return
    if not frag.children:
        return
    first = frag.children[0]
    node.name = first.name
    node.attrs = _merge_attrs(first.attrs, node.attrs)
    if node.text is None:
        node.text = first.text
    node.self_closing = node.self_closing or first.self_closing
    own_children = node.children
    node.children = []
    for c in first.children + own_children:
        node.add(c)
    _apply_snippet(node, ctx, depth + 1)


def _resolve(node, parent_name, ctx):
    if node.lorem is None:
        if node.name is None:
            if node.attrs or node.implicit:
                node.name = _implicit_name(parent_name, ctx.syntax)
                _apply_snippet(node, ctx)
        else:
            _apply_snippet(node, ctx)
    for c in list(node.children):
        _resolve(c, node.name, ctx)


# ------------------------------------------------------------------ helpers

_NUM_RE = re.compile(r"(\$+)(?:@(-)?(\d*))?")
_PLACEHOLDER_RE = re.compile(r"\$\{(\w+)(?::([^}]*))?\}")


class Stop:
    __slots__ = ("default",)

    def __init__(self, default=""):
        self.default = default


def _number(text, reps):
    if "$" not in text:
        return text
    index, count = reps[-1] if reps else (1, 1)
    escaped = text.replace("\\$", "\x00")

    def sub(m):
        width = len(m.group(1))
        reverse = bool(m.group(2))
        base = int(m.group(3)) if m.group(3) else 1
        value = base + count - index if reverse else base + index - 1
        return str(value).zfill(width)

    return _NUM_RE.sub(sub, escaped).replace("\x00", "$")


def _value_parts(value, reps, seen):
    """Split a value into text (with $ numbering applied) and tab stops."""
    parts = []
    pos = 0
    for m in _PLACEHOLDER_RE.finditer(value):
        if m.start() > pos:
            parts.append(_number(value[pos:m.start()], reps))
        name, default = m.group(1), m.group(2) or ""
        if name in D.VARIABLES:
            parts.append(D.VARIABLES[name])
        elif name in seen:
            parts.append(default)
        else:
            seen.add(name)
            parts.append(Stop(default))
        pos = m.end()
    if pos < len(value):
        parts.append(_number(value[pos:], reps))
    return parts


def _quote(text):
    if '"' in text and "'" not in text:
        return "'"
    return '"'


def _lorem_text(count, ctx):
    rng = ctx.rng
    if ctx.first_lorem:
        words = [D.LOREM_WORDS[i % len(D.LOREM_WORDS)] for i in range(count)]
        ctx.first_lorem = False
    else:
        words = [rng.choice(D.LOREM_WORDS) for _ in range(count)]
    sentences = []
    i = 0
    while i < len(words):
        remaining = len(words) - i
        size = rng.randint(6, 12)
        if remaining - size < 4:
            size = remaining
        chunk = words[i:i + size]
        if len(chunk) > 6 and rng.random() < 0.5:
            chunk[len(chunk) // 2 - 1] += ","
        chunk[0] = chunk[0][:1].upper() + chunk[0][1:]
        sentences.append(" ".join(chunk).rstrip(",") + ".")
        i += size
    return " ".join(sentences)


# ---------------------------------------------------------- html-like output

class _HtmlRenderer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.pad = ctx.pad
        self.syntax = ctx.syntax
        self._break_memo = {}

    def render(self, nodes):
        return self._siblings(nodes, 0, [])

    # -- layout decisions
    def _is_block(self, n):
        return n.name is not None and n.name.lower() not in self.ctx.inline

    def _text_of(self, n):
        if n.lorem is not None:
            return None
        return n.text

    def _multiline_text(self, n):
        if not n.text:
            return False
        return "\n" in n.text or (n.wrapped_markup and self._is_block(n))

    def _needs_break(self, n):
        key = id(n)
        if key in self._break_memo:
            return self._break_memo[key]
        result = (
            self._is_block(n)
            or self._multiline_text(n)
            or self._has_comment(n)
            or any(self._needs_break(c) for c in n.children)
        )
        self._break_memo[key] = result
        return result

    def _has_comment(self, n):
        return "c" in self.ctx.filters and n.name and (n.attr("id") or n.attr("class"))

    # -- rendering
    def _siblings(self, nodes, level, reps):
        parts = []
        prev = None
        for n in nodes:
            if prev is not None and (self._needs_break(prev) or self._needs_break(n)):
                parts.append("\n" + self.pad * level)
            parts.extend(self._node(n, level, reps))
            prev = n
        return parts

    def _node(self, n, level, reps):
        reps = reps + n.reps
        if n.lorem is not None:
            return [_lorem_text(n.lorem, self.ctx)]
        if n.name is None:
            return self._text_parts(n.text or "", n, reps, level)
        return self._element(n, level, reps)

    def _text_parts(self, text, n, reps, level):
        seen = set()
        if "\n" in text:
            lines = text.split("\n")
            common = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
            out = []
            for idx, line in enumerate(lines):
                if idx:
                    out.append("\n" + self.pad * level)
                out.extend(_value_parts(line[common:], reps, seen))
            return out
        return _value_parts(text, reps, seen)

    def _attr_name(self, name):
        if self.syntax == "jsx":
            return {"class": "className", "for": "htmlFor"}.get(name, name)
        return name

    def _attrs(self, n, reps):
        parts = []
        seen = set()
        for a in n.attrs:
            if a.excluded:
                continue
            name = self._attr_name(a.name)
            if a.value is None:
                if a.boolean or a.name.lower() in D.BOOLEAN_ATTRS:
                    parts.append(" " + name)
                else:
                    parts += [" " + name + '="', Stop(""), '"']
                continue
            vparts = _value_parts(a.value, reps, seen)
            flat = "".join(p for p in vparts if isinstance(p, str))
            q = _quote(flat)
            parts += [" " + name + "=" + q] + vparts + [q]
        return parts

    def _is_void(self, n):
        if self.syntax in ("xml", "xsl"):
            return n.self_closing
        return n.self_closing or n.name.lower() in D.VOID_ELEMENTS

    def _element(self, n, level, reps):
        name = n.name
        opening = ["<" + name] + self._attrs(n, reps)
        if self._is_void(n):
            if self.syntax == "jsx":
                return opening + [" />"]
            if self.syntax in ("xml", "xsl"):
                return opening + ["/>"]
            return opening + [">"]
        closing = "</" + name + ">"
        text_parts = self._text_parts(n.text, n, reps, level + 1) if n.text else []
        if not n.children and not n.text:
            out = opening + [">", Stop(""), closing]
        elif not any(self._needs_break(c) for c in n.children) and not self._multiline_text(n):
            out = opening + [">"] + text_parts + self._siblings(n.children, level, reps) + [closing]
        else:
            inner = []
            if n.text and self._multiline_text(n):
                inner += ["\n" + self.pad * (level + 1)] + text_parts
            elif n.text:
                inner += text_parts
            if n.children:
                inner += ["\n" + self.pad * (level + 1)] + self._siblings(n.children, level + 1, reps)
            out = opening + [">"] + inner + ["\n" + self.pad * level, closing]
        if self._has_comment(n):
            label = ""
            idv = n.attr("id")
            if idv and idv.value:
                label += "#" + _number(idv.value, reps)
            cls = n.attr("class")
            if cls and cls.value:
                label += "." + ".".join(_number(cls.value, reps).split())
            out += ["\n" + self.pad * level, f"<!-- /{label} -->"]
        return out


# ------------------------------------------------------- indentation syntaxes

class _IndentRenderer:
    """Pug, HAML and Slim: one element per line, nesting by indentation."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.pad = ctx.pad
        self.syntax = ctx.syntax

    def render(self, nodes):
        return self._nodes(nodes, 0, [])

    def _nodes(self, nodes, level, reps):
        parts = []
        for idx, n in enumerate(nodes):
            if idx:
                parts.append("\n")
            parts.extend(self._node(n, level, reps))
        return parts

    def _shorthand(self, n, reps):
        seen = set()
        ident = ""
        classes = []
        others = []
        for a in n.attrs:
            if a.excluded:
                continue
            if a.value is None:
                value = None if (a.boolean or a.name.lower() in D.BOOLEAN_ATTRS) else ""
            else:
                value = "".join(p for p in _value_parts(a.value, reps, set()) if isinstance(p, str))
            if a.name == "id" and value:
                ident = value
            elif a.name == "class" and value:
                classes += value.split()
            else:
                others.append((a, value))
        return ident, classes, others

    def _node(self, n, level, reps):
        reps = reps + n.reps
        indent = self.pad * level
        text = None
        if n.lorem is not None:
            text = _lorem_text(n.lorem, self.ctx)
        elif n.name is None:
            text = "".join(p for p in _value_parts(n.text or "", reps, set()) if isinstance(p, str))
        if text is not None:
            marker = "" if self.syntax == "haml" else "| "
            return [indent + marker + text]
        ident, classes, others = self._shorthand(n, reps)
        short = ("#" + ident if ident else "") + "".join("." + c for c in classes)
        omit_name = n.name == "div" and short
        if self.syntax == "haml":
            head = ("" if omit_name else "%" + n.name) + short
            if others:
                head += "{" + ", ".join(self._haml_attr(a, v) for a, v in others) + "}"
        elif self.syntax == "slim":
            head = ("" if omit_name else n.name) + short
            for a, v in others:
                head += " " + a.name + ("" if v is None else '="' + v + '"')
        else:  # pug
            head = ("" if omit_name else n.name) + short
            if others:
                head += "(" + " ".join(a.name if v is None else f'{a.name}="{v}"' for a, v in others) + ")"
        parts = [indent + head]
        n_text = None
        if n.text:
            n_text = "".join(p for p in _value_parts(n.text, reps, set()) if isinstance(p, str))
        if n_text:
            parts.append(" " + n_text)
        elif not n.children:
            parts.append(Stop(""))
        if n.children:
            parts.append("\n")
            parts.extend(self._nodes(n.children, level + 1, reps))
        return parts

    @staticmethod
    def _haml_attr(attr, value):
        if value is None:
            return f"{attr.name}: true"
        return f'{attr.name}: "{value}"'


# --------------------------------------------------------------- public API

def _split_filters(abbr):
    depth = 0
    quote = None
    for i, c in enumerate(abbr):
        if quote:
            if c == quote:
                quote = None
            continue
        if c in "\"'" and depth > 0:
            quote = c
        elif c in "[{(":
            depth += 1
        elif c in "]})":
            depth -= 1
        elif c == "|" and depth == 0:
            return abbr[:i], [f for f in abbr[i + 1:].split("|") if f]
    return abbr, []


def _finalize(parts):
    text = []
    stops = []
    length = 0
    for p in parts:
        if isinstance(p, Stop):
            stops.append((length, length + len(p.default)))
            text.append(p.default)
            length += len(p.default)
        else:
            text.append(p)
            length += len(p)
    return Expansion("".join(text), stops)


def _document(base, syntax, indent):
    if syntax not in ("html", "jsx"):
        return None
    m = re.fullmatch(r"!!!(\w*)", base)
    if m and m.group(1) in D.DOCTYPES:
        return Expansion(D.DOCTYPES[m.group(1)], [])
    template = D.DOCUMENTS.get(base)
    if template is None:
        return None
    for token, key in D.DOCUMENT_DOCTYPE_KEYS.items():
        template = template.replace(token, D.DOCTYPES[key])
    template = template.replace("{P}", indent)
    marker = template.index("${0}")
    return Expansion(template.replace("${0}", ""), [(marker, marker)])


_INDENT_DOCS = {
    "pug": "doctype html\n",
    "haml": "!!! 5\n",
    "slim": "doctype html\n",
}
_DOC_ABBR = "html[lang=en]>(head>meta[charset=UTF-8]+meta:vp+title{Document})+body"


def _apply_content(root, content):
    def last_leaf(n):
        while n.children:
            n = n.children[-1]
        return n

    def find_lines_node(n):
        if n.mult_lines:
            return n
        for c in n.children:
            r = find_lines_node(c)
            if r:
                return r
        return None

    top = find_lines_node(root)
    lines = [l for l in content.split("\n") if l.strip()]
    if top is not None and len(lines) > 1:
        parent = top.parent
        idx = parent.children.index(top)
        copies = []
        for k, line in enumerate(lines, 1):
            c = top.copy()
            c.mult_lines = False
            c.reps.insert(0, (k, len(lines)))
            leaf = last_leaf(c)
            leaf.text = line.strip()
            leaf.wrapped_markup = leaf.text.startswith("<")
            copies.append(c)
        parent.children[idx:idx + 1] = copies
        for c in copies:
            c.parent = parent
        return
    if not root.children:
        return
    leaf = last_leaf(root.children[-1])
    if leaf.lorem is None:
        leaf.text = content.strip("\n") if "\n" in content else content
        leaf.wrapped_markup = leaf.text.lstrip().startswith("<")


def expand(abbr, syntax="html", indent="    ", content=None, seed=None):
    """Expand a markup abbreviation. Returns an Expansion, or None if invalid."""
    if syntax not in MARKUP_SYNTAXES:
        syntax = "html"
    abbr = abbr.strip()
    if not abbr:
        return None
    base, filters = _split_filters(abbr)
    doc = _document(base, syntax, indent) if content is None else None
    if doc is not None:
        return doc
    prefix = ""
    if base in ("!", "html:5") and syntax in _INDENT_DOCS:
        prefix = _INDENT_DOCS[syntax]
        base = _DOC_ABBR
    expando = False
    if base.endswith("+") and len(base) > 1:
        expando = True
        base = base[:-1]
    try:
        root = _Parser(base, expando).parse()
    except EmmetError:
        return None
    if not root.children:
        return None
    ctx = _Ctx(syntax, indent, filters, random.Random(seed))
    for child in list(root.children):
        _resolve(child, None, ctx)
    if content is not None:
        _apply_content(root, content)
    renderer = _IndentRenderer(ctx) if syntax in ("pug", "haml", "slim") else _HtmlRenderer(ctx)
    parts = renderer.render(root.children)
    if "e" in filters:
        parts = [_html.escape(p, quote=False) if isinstance(p, str) else p for p in parts]
    if prefix:
        parts.insert(0, prefix)
    return _finalize(parts)
