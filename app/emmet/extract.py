"""Finding the abbreviation before the cursor, and deciding which Emmet syntax applies."""
import re

from . import markup_data as D

_MARKUP_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#.>+*^$@!:_-/|%"
)
_LEADING_OPERATORS = ">+^*-/|@$%:"

KNOWN_WORDS = set(D.HTML_SNIPPETS) | set(D.XSL_SNIPPETS) | {
    "html", "head", "body", "title", "div", "span", "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "dl", "dt", "dd", "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "caption", "colgroup", "form", "input", "button", "select", "option", "optgroup",
    "textarea", "label", "fieldset", "legend", "a", "img", "br", "hr", "em", "strong", "b",
    "i", "u", "s", "small", "sub", "sup", "code", "pre", "kbd", "samp", "var", "cite", "q",
    "blockquote", "abbr", "address", "article", "aside", "footer", "header", "main", "nav",
    "section", "figure", "figcaption", "details", "summary", "dialog", "template", "slot",
    "canvas", "svg", "video", "audio", "source", "track", "iframe", "embed", "object",
    "param", "picture", "map", "area", "meta", "link", "style", "script", "noscript", "base",
    "mark", "time", "data", "ruby", "rt", "rp", "bdi", "bdo", "wbr", "del", "ins", "output",
    "progress", "meter", "datalist", "menu", "center", "font", "big", "tt", "strike",
}

_PURE_WORD = re.compile(r"[A-Za-z][\w-]*")


def extract_markup(prefix):
    """Return (start_index, abbreviation) for the markup abbreviation ending at the end of prefix."""
    i = len(prefix)
    stack = []
    while i > 0:
        c = prefix[i - 1]
        if stack:
            top = stack[-1]
            if top in "[{":
                closing = "]" if top == "[" else "}"
                if c == top:
                    stack.pop()
                elif c == closing:
                    stack.append(top)
                i -= 1
                continue
            if c == "(":
                stack.pop()
            elif c == ")":
                stack.append("(")
            elif c == "]":
                stack.append("[")
            elif c == "}":
                stack.append("{")
            elif c not in _MARKUP_CHARS:
                return None
            i -= 1
            continue
        if c == ")":
            stack.append("(")
        elif c == "]":
            stack.append("[")
        elif c == "}":
            stack.append("{")
        elif c == ">":
            k = prefix.rfind("<", 0, i - 1)
            if k != -1 and ">" not in prefix[k + 1:i - 1]:
                break
        elif c not in _MARKUP_CHARS:
            break
        i -= 1
    if stack:
        return None
    start = i
    while start < len(prefix) and prefix[start] in _LEADING_OPERATORS:
        start += 1
    abbr = prefix[start:]
    if not abbr:
        return None
    if _PURE_WORD.fullmatch(abbr) and abbr not in KNOWN_WORDS:
        if prefix[:start].strip():
            return None
    return start, abbr


def extract_css(prefix):
    """Return (start_index, abbreviation) for the CSS abbreviation ending at the end of prefix."""
    i = len(prefix)
    depth = 0
    while i > 0:
        c = prefix[i - 1]
        if c == ")":
            depth += 1
        elif c == "(":
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and (c.isspace() or c in ";{},"):
            break
        i -= 1
    abbr = prefix[i:]
    if not abbr or depth != 0:
        return None
    return i, abbr


# ------------------------------------------------------------------ contexts

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_STRING_RE = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'')


def css_block_depth(text):
    """How many CSS rule blocks the end of `text` is inside."""
    cleaned = _COMMENT_RE.sub("", text)
    cleaned = _STRING_RE.sub('""', cleaned)
    return cleaned.count("{") - cleaned.count("}")


def html_context(text_before):
    """'html' when markup abbreviations apply; ('css', text) inside <style>; None in tags/scripts/comments."""
    last_open = text_before.rfind("<!--")
    if last_open > text_before.rfind("-->"):
        return None
    for tag in ("script", "style"):
        opens = list(re.finditer(rf"<{tag}\b[^>]*>", text_before, re.I))
        closes = list(re.finditer(rf"</{tag}\s*>", text_before, re.I))
        if opens and (not closes or opens[-1].end() > closes[-1].start()):
            if tag == "script":
                return None
            return ("css", text_before[opens[-1].end():])
    if text_before.rfind("<") > text_before.rfind(">"):
        return None
    return "html"


MARKUP_LANGUAGES = {
    "html": "html", "xml": "xml", "xsl": "xsl", "jsx": "jsx",
    "pug": "pug", "haml": "haml", "slim": "slim",
}
CSS_LANGUAGES = {"css": "css", "sass": "sass", "stylus": "stylus"}


def resolve_context(language, text_before):
    """Return (kind, syntax, css_text) or None. kind is 'markup' or 'css'."""
    if language == "html":
        ctx = html_context(text_before)
        if ctx is None:
            return None
        if isinstance(ctx, tuple):
            return "css", "css", ctx[1]
        return "markup", "html", None
    if language in MARKUP_LANGUAGES:
        return "markup", MARKUP_LANGUAGES[language], None
    if language in CSS_LANGUAGES:
        return "css", CSS_LANGUAGES[language], text_before
    return None
