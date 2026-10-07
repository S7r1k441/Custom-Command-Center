"""Syntax highlighters for the code editor (Python, HTML, CSS, JS, JSON, Markdown)."""
import builtins
import keyword

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Bold)
    fmt.setFontItalic(italic)
    return fmt


def _rx(pattern: str) -> QRegularExpression:
    return QRegularExpression(pattern)


def _apply(hl, text: str, regex: QRegularExpression, fmt, group: int = 0, offset: int = 0):
    it = regex.globalMatch(text)
    while it.hasNext():
        m = it.next()
        start = m.capturedStart(group)
        if start >= 0:
            hl.setFormat(offset + start, m.capturedLength(group), fmt)


def _find_line_comment(text: str, marker: str) -> int:
    """Index of a line-comment marker that isn't inside a quoted string, else -1."""
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "'\"`":
            quote = c
        elif text.startswith(marker, i):
            return i
        i += 1
    return -1


def _block_comments(hl, text: str, start: str, end: str, fmt) -> list[tuple[int, int]]:
    """Format multi-line comments using block state 1; returns the commented spans."""
    spans = []
    pos = 0
    hl.setCurrentBlockState(0)
    if hl.previousBlockState() == 1:
        close = text.find(end)
        if close == -1:
            hl.setFormat(0, len(text), fmt)
            hl.setCurrentBlockState(1)
            return [(0, len(text))]
        pos = close + len(end)
        hl.setFormat(0, pos, fmt)
        spans.append((0, pos))
    while True:
        s = text.find(start, pos)
        if s == -1:
            break
        close = text.find(end, s + len(start))
        if close == -1:
            hl.setFormat(s, len(text) - s, fmt)
            hl.setCurrentBlockState(1)
            spans.append((s, len(text)))
            break
        pos = close + len(end)
        hl.setFormat(s, pos - s, fmt)
        spans.append((s, pos))
    return spans


class _BaseHighlighter(QSyntaxHighlighter):
    def __init__(self, document, palette: dict):
        super().__init__(document)
        self.set_palette(palette)

    def set_palette(self, palette: dict):
        self._build(palette)
        self.rehighlight()

    def _build(self, palette: dict):
        raise NotImplementedError


class PythonHighlighter(_BaseHighlighter):
    def _build(self, palette: dict):
        self.rules = []
        kw_fmt = _fmt(palette["keyword"], bold=True)
        for word in keyword.kwlist:
            self.rules.append((_rx(rf"\b{word}\b"), kw_fmt))

        builtin_fmt = _fmt(palette["builtin"])
        for name in dir(builtins):
            if not name.startswith("_"):
                self.rules.append((_rx(rf"\b{name}\b"), builtin_fmt))

        self.rules.append((_rx(r"\bself\b|\bcls\b"), _fmt(palette["self"], italic=True)))
        self.rules.append((_rx(r"\b\d+\.?\d*\b"), _fmt(palette["number"])))
        self.rules.append((_rx(r"@\w+"), _fmt(palette["decorator"])))
        self.rules.append((_rx(r"\bdef\s+(\w+)"), _fmt(palette["def_name"], bold=True)))
        self.rules.append((_rx(r"\bclass\s+(\w+)"), _fmt(palette["def_name"], bold=True)))
        self.rules.append((_rx(r"'[^'\\]*(\\.[^'\\]*)*'"), _fmt(palette["string"])))
        self.rules.append((_rx(r'"[^"\\]*(\\.[^"\\]*)*"'), _fmt(palette["string"])))
        self.comment_fmt = _fmt(palette["comment"], italic=True)

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.rules:
            _apply(self, text, pattern, fmt)
        idx = _find_line_comment(text, "#")
        if idx >= 0:
            self.setFormat(idx, len(text) - idx, self.comment_fmt)


class HtmlHighlighter(_BaseHighlighter):
    """Block state: 0 = normal, 1 = inside <!-- comment -->, 2 = inside a tag."""

    def _build(self, p: dict):
        self.f_tag = _fmt(p.get("tag", p["keyword"]), bold=True)
        self.f_attr = _fmt(p["builtin"])
        self.f_str = _fmt(p["string"])
        self.f_comment = _fmt(p["comment"], italic=True)
        self.f_entity = _fmt(p["number"])
        self.f_decl = _fmt(p["decorator"])
        self.attr_re = _rx(r"[A-Za-z_:@][\w:.@-]*(?=\s*=)")
        self.str_re = _rx(r"\"[^\"]*\"|'[^']*'")
        self.entity_re = _rx(r"&#?\w+;")

    def _format_tag(self, text: str, start: int, stop: int):
        segment = text[start:stop]
        self.setFormat(start, stop - start, self.f_decl if segment.startswith("<!") else self.f_tag)
        _apply(self, segment, self.attr_re, self.f_attr, offset=start)
        _apply(self, segment, self.str_re, self.f_str, offset=start)

    def highlightBlock(self, text: str) -> None:
        n = len(text)
        _apply(self, text, self.entity_re, self.f_entity)
        prev = self.previousBlockState()
        pos = 0
        if prev == 1:
            end = text.find("-->")
            if end == -1:
                self.setFormat(0, n, self.f_comment)
                self.setCurrentBlockState(1)
                return
            pos = end + 3
            self.setFormat(0, pos, self.f_comment)
        elif prev == 2:
            end = text.find(">")
            stop = n if end == -1 else end + 1
            self._format_tag(text, 0, stop)
            if end == -1:
                self.setCurrentBlockState(2)
                return
            pos = stop

        while pos < n:
            lt = text.find("<", pos)
            if lt == -1:
                break
            if text.startswith("<!--", lt):
                end = text.find("-->", lt + 4)
                if end == -1:
                    self.setFormat(lt, n - lt, self.f_comment)
                    self.setCurrentBlockState(1)
                    return
                self.setFormat(lt, end + 3 - lt, self.f_comment)
                pos = end + 3
                continue
            if lt + 1 >= n or not (text[lt + 1].isalpha() or text[lt + 1] in "/!?"):
                pos = lt + 1
                continue
            gt = text.find(">", lt + 1)
            stop = n if gt == -1 else gt + 1
            self._format_tag(text, lt, stop)
            if gt == -1:
                self.setCurrentBlockState(2)
                return
            pos = stop
        self.setCurrentBlockState(0)


class CssHighlighter(_BaseHighlighter):
    """Block state: (brace depth << 1) | inside-comment flag."""

    def _build(self, p: dict):
        self.f_comment = _fmt(p["comment"], italic=True)
        f_str = _fmt(p["string"])
        f_num = _fmt(p["number"])
        self.selector_rules = [
            (_rx(r"\[[^\]]*\]"), _fmt(p["builtin"]), 0),
            (_rx(r"::?[A-Za-z-]+"), _fmt(p["decorator"]), 0),
            (_rx(r"[.#][A-Za-z_-][\w-]*"), _fmt(p["def_name"], bold=True), 0),
            (_rx(r"@[\w-]+"), _fmt(p["keyword"], bold=True), 0),
            (_rx(r"\"[^\"]*\"|'[^']*'"), f_str, 0),
        ]
        self.declaration_rules = [
            (_rx(r"(?<![\w#-])-?\d*\.?\d+[A-Za-z%]*"), f_num, 0),
            (_rx(r"#[0-9a-fA-F]{3,8}\b"), f_num, 0),
            (_rx(r"[A-Za-z-]+(?=\()"), _fmt(p["decorator"]), 0),
            (_rx(r"!\s*important"), _fmt(p["keyword"], bold=True), 0),
            (_rx(r"\"[^\"]*\"|'[^']*'"), f_str, 0),
            (_rx(r"(?:^|;)\s*([A-Za-z-]+)\s*:"), _fmt(p["builtin"]), 1),
        ]

    def _format_segment(self, text: str, start: int, end: int, depth: int, opens_block: bool):
        if start >= end:
            return
        segment = text[start:end]
        rules = self.selector_rules if (depth == 0 or opens_block) else self.declaration_rules
        for regex, fmt, group in rules:
            _apply(self, segment, regex, fmt, group=group, offset=start)

    def highlightBlock(self, text: str) -> None:
        state = max(self.previousBlockState(), 0)
        depth = state >> 1
        in_comment = bool(state & 1)
        n = len(text)
        i = 0
        seg = 0
        while i < n:
            if in_comment:
                end = text.find("*/", i)
                if end == -1:
                    self.setFormat(i, n - i, self.f_comment)
                    i = seg = n
                    break
                self.setFormat(i, end + 2 - i, self.f_comment)
                i = seg = end + 2
                in_comment = False
                continue
            if text.startswith("/*", i):
                self._format_segment(text, seg, i, depth, False)
                self.setFormat(i, 2, self.f_comment)
                in_comment = True
                i += 2
                seg = i
                continue
            c = text[i]
            if c == "{":
                self._format_segment(text, seg, i, depth, True)
                depth += 1
                i += 1
                seg = i
            elif c == "}":
                self._format_segment(text, seg, i, depth, False)
                depth = max(0, depth - 1)
                i += 1
                seg = i
            else:
                i += 1
        if not in_comment:
            self._format_segment(text, seg, n, depth, False)
        self.setCurrentBlockState((depth << 1) | (1 if in_comment else 0))


JS_KEYWORDS = (
    "async await break case catch class const continue debugger default delete do else export "
    "extends finally for function if import in instanceof let new of return static super switch "
    "this throw try typeof var void while with yield null undefined true false NaN Infinity"
).split()
JS_BUILTINS = (
    "console document window Math JSON Array Object String Number Boolean Promise Date RegExp Map "
    "Set Error parseInt parseFloat setTimeout setInterval clearTimeout clearInterval fetch "
    "localStorage sessionStorage alert prompt confirm require module exports"
).split()


class JavaScriptHighlighter(_BaseHighlighter):
    def _build(self, p: dict):
        self.rules = []
        kw = _fmt(p["keyword"], bold=True)
        for word in JS_KEYWORDS:
            self.rules.append((_rx(rf"\b{word}\b"), kw))
        bi = _fmt(p["builtin"])
        for word in JS_BUILTINS:
            self.rules.append((_rx(rf"\b{word}\b"), bi))
        self.rules.append((_rx(r"\b0x[0-9a-fA-F]+\b|\b\d+\.?\d*\b"), _fmt(p["number"])))
        self.rules.append((_rx(r"\bfunction\s+([A-Za-z_$][\w$]*)"), _fmt(p["def_name"], bold=True)))
        self.rules.append((_rx(r"\bclass\s+([A-Za-z_$][\w$]*)"), _fmt(p["def_name"], bold=True)))
        f_str = _fmt(p["string"])
        self.rules.append((_rx(r"'[^'\\]*(\\.[^'\\]*)*'"), f_str))
        self.rules.append((_rx(r'"[^"\\]*(\\.[^"\\]*)*"'), f_str))
        self.rules.append((_rx(r"`[^`\\]*(\\.[^`\\]*)*`"), f_str))
        self.comment_fmt = _fmt(p["comment"], italic=True)

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.rules:
            _apply(self, text, pattern, fmt)
        spans = _block_comments(self, text, "/*", "*/", self.comment_fmt)
        idx = _find_line_comment(text, "//")
        if idx >= 0 and not any(s <= idx < e for s, e in spans):
            self.setFormat(idx, len(text) - idx, self.comment_fmt)


class JsonHighlighter(_BaseHighlighter):
    def _build(self, p: dict):
        self.rules = [
            (_rx(r"-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"), _fmt(p["number"]), 0),
            (_rx(r"\b(?:true|false|null)\b"), _fmt(p["keyword"], bold=True), 0),
            (_rx(r"\"(?:[^\"\\]|\\.)*\""), _fmt(p["string"]), 0),
            (_rx(r"\"(?:[^\"\\]|\\.)*\"(?=\s*:)"), _fmt(p["builtin"]), 0),
        ]

    def highlightBlock(self, text: str) -> None:
        for regex, fmt, group in self.rules:
            _apply(self, text, regex, fmt, group=group)


class MarkdownHighlighter(_BaseHighlighter):
    """Block state: 0 = normal, 1 = inside a fenced code block."""

    def _build(self, p: dict):
        self.f_code = _fmt(p["string"])
        self.rules = [
            (_rx(r"^\s*(?:[-*+]|\d+\.)\s"), _fmt(p["number"], bold=True)),
            (_rx(r"\[[^\]]*\]\([^)]*\)"), _fmt(p["builtin"])),
            (_rx(r"(?<!\*)\*[^*\s][^*]*\*(?!\*)|(?<!_)_[^_\s][^_]*_(?!_)"), _fmt(p["self"], italic=True)),
            (_rx(r"\*\*[^*]+\*\*|__[^_]+__"), _fmt(p["def_name"], bold=True)),
            (_rx(r"`[^`]+`"), self.f_code),
            (_rx(r"^\s*>.*$"), _fmt(p["comment"], italic=True)),
            (_rx(r"^#{1,6}\s.*$"), _fmt(p["keyword"], bold=True)),
        ]

    def highlightBlock(self, text: str) -> None:
        in_code = self.previousBlockState() == 1
        if text.lstrip().startswith("```"):
            self.setFormat(0, len(text), self.f_code)
            self.setCurrentBlockState(0 if in_code else 1)
            return
        if in_code:
            self.setFormat(0, len(text), self.f_code)
            self.setCurrentBlockState(1)
            return
        self.setCurrentBlockState(0)
        for regex, fmt in self.rules:
            _apply(self, text, regex, fmt)


class JsxHighlighter(JavaScriptHighlighter):
    def _build(self, p: dict):
        super()._build(p)
        tag = _fmt(p.get("tag", p["keyword"]), bold=True)
        strings_start = len(self.rules) - 3
        self.rules.insert(strings_start, (_rx(r"</?[A-Za-z][\w.-]*|/?>"), tag))


_HIGHLIGHTERS = {
    "python": PythonHighlighter,
    "html": HtmlHighlighter,
    "xml": HtmlHighlighter,
    "xsl": HtmlHighlighter,
    "jsx": JsxHighlighter,
    "css": CssHighlighter,
    "javascript": JavaScriptHighlighter,
    "json": JsonHighlighter,
    "markdown": MarkdownHighlighter,
}


def create_highlighter(document, language: str, palette: dict):
    cls = _HIGHLIGHTERS.get(language)
    return cls(document, palette) if cls else None
