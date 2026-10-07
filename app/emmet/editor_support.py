"""Qt glue: Emmet abbreviation expansion, tab stops and editor actions for CodeEditor."""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader, QTextCursor
from PySide6.QtWidgets import QInputDialog

from . import actions, markup, stylesheet, tags
from .extract import css_block_depth, extract_css, extract_markup, resolve_context
from .common import Edit

INDENT = "    "
STRUCT_HTML = {"html", "xml", "xsl", "jsx"}
STRUCT_CSS = {"css", "sass", "stylus"}


def _utf16_len(s):
    return len(s.encode("utf-16-le", "surrogatepass")) // 2


def py_to_qt(text, i):
    return _utf16_len(text[:i])


def qt_to_py(text, pos):
    if pos <= 0:
        return 0
    units = 0
    for idx, ch in enumerate(text):
        if units >= pos:
            return idx
        units += 2 if ord(ch) > 0xFFFF else 1
    return len(text)


def indent_expansion(exp, base):
    """Indent every line after the first by the line's existing indentation."""
    if not base or "\n" not in exp.text:
        return exp.text, list(exp.stops)
    newlines = [i for i, ch in enumerate(exp.text) if ch == "\n"]

    def shifted(offset):
        return offset + len(base) * sum(1 for p in newlines if p < offset)

    return exp.text.replace("\n", "\n" + base), [(shifted(a), shifted(b)) for a, b in exp.stops]


class EmmetMixin:
    emmet_enabled = True
    base_dir = None

    # ---- state
    def _init_emmet(self):
        self._stops = []
        self._stops_span = None

    def set_emmet_enabled(self, enabled):
        self.emmet_enabled = enabled
        if not enabled:
            self._clear_stops()

    def _message(self, text):
        self.emmet_message.emit(text)

    # ---- text/selection helpers (Python string indices <-> Qt positions)
    def _text_and_selection(self):
        text = self.toPlainText()
        cur = self.textCursor()
        return text, qt_to_py(text, cur.selectionStart()), qt_to_py(text, cur.selectionEnd())

    def _replace_range(self, start, end, new_text, sel_start, sel_end):
        """Replace text[start:end] in one undo step, then select sel_start..sel_end (in the new text)."""
        text = self.toPlainText()
        new_doc = text[:start] + new_text + text[end:]
        cur = self.textCursor()
        cur.beginEditBlock()
        cur.setPosition(py_to_qt(text, start))
        cur.setPosition(py_to_qt(text, end), QTextCursor.KeepAnchor)
        cur.insertText(new_text)
        cur.endEditBlock()
        sel = QTextCursor(self.document())
        sel.setPosition(py_to_qt(new_doc, sel_start))
        sel.setPosition(py_to_qt(new_doc, sel_end), QTextCursor.KeepAnchor)
        self.setTextCursor(sel)
        return new_doc

    def apply_emmet_edit(self, edit):
        if edit is None:
            return False
        self._clear_stops()
        self._replace_range(edit.start, edit.end, edit.text, edit.sel_start, edit.sel_end)
        return True

    # ---- tab stops
    def _clear_stops(self):
        self._stops = []
        self._stops_span = None

    def _set_stops(self, new_doc, stops, span_start, span_end):
        cursors = []
        for a, b in stops:
            c = QTextCursor(self.document())
            c.setPosition(py_to_qt(new_doc, a))
            c.setPosition(py_to_qt(new_doc, b), QTextCursor.KeepAnchor)
            cursors.append(c)
        start_c = QTextCursor(self.document())
        start_c.setPosition(py_to_qt(new_doc, span_start))
        end_c = QTextCursor(self.document())
        end_c.setPosition(py_to_qt(new_doc, span_end))
        self._stops = cursors
        self._stops_span = (start_c, end_c)

    def _next_stop(self):
        if not self._stops:
            return False
        cursor = self._stops.pop(0)
        self.setTextCursor(cursor)
        if not self._stops:
            self._stops_span = None
        return True

    def _in_stop_span(self):
        if not self._stops or self._stops_span is None:
            return False
        pos = self.textCursor().position()
        return self._stops_span[0].position() <= pos <= self._stops_span[1].position()

    # ---- Tab key entry point
    def emmet_tab(self):
        """Handle Tab: jump to the next tab stop, or expand an abbreviation. False = do normal Tab."""
        if self._stops:
            if self._in_stop_span():
                return self._next_stop()
            self._clear_stops()
        if not self.emmet_enabled:
            return False
        return self.expand_abbreviation()

    def _abbreviation_before_cursor(self):
        cur = self.textCursor()
        if cur.hasSelection():
            return None
        text = self.toPlainText()
        pos = qt_to_py(text, cur.position())
        before = text[:pos]
        ctx = resolve_context(self.language, before)
        if ctx is None:
            return None
        kind, syntax, css_text = ctx
        line_start = before.rfind("\n") + 1
        prefix = before[line_start:]
        if kind == "css":
            if syntax == "css" and css_block_depth(css_text) <= 0 and not prefix.lstrip().startswith("@"):
                return None
            found = extract_css(prefix)
        else:
            found = extract_markup(prefix)
        if not found:
            return None
        start, abbr = found
        return kind, syntax, abbr, line_start + start, pos, prefix

    def expand_abbreviation(self):
        info = self._abbreviation_before_cursor()
        if info is None:
            return False
        kind, syntax, abbr, start, end, prefix = info
        if kind == "css":
            exp = stylesheet.expand(abbr, syntax, INDENT)
        else:
            exp = markup.expand(abbr, syntax, INDENT)
        if exp is None:
            return False
        base = prefix[: len(prefix) - len(prefix.lstrip())]
        out, stops = indent_expansion(exp, base)
        self._insert_expansion(start, end, out, stops)
        return True

    def _insert_expansion(self, start, end, out, stops):
        text = self.toPlainText()
        abs_stops = [(start + a, start + b) for a, b in stops]
        final = start + len(out)
        new_doc = self._replace_range(start, end, out, final, final)
        self._clear_stops()
        if abs_stops:
            self._set_stops(new_doc, abs_stops, start, final)
            self._next_stop()

    # ---- actions
    def _structure_language(self):
        if self.language in STRUCT_HTML:
            return "html"
        if self.language in STRUCT_CSS:
            return "css"
        return self.language

    def wrap_with_abbreviation(self):
        if self.language not in STRUCT_HTML:
            self._message("Wrap with Abbreviation works in HTML, XML and JSX files.")
            return
        text, s, e = self._text_and_selection()
        if s == e:
            el = tags.enclosing(tags.scan(text), s)
            if el is not None:
                s, e = el.open_start, el.end
            else:
                ls, le = tags._line_bounds(text, s)
                s, e = ls + (len(text[ls:le]) - len(text[ls:le].lstrip())), le
        if s >= e:
            self._message("Nothing to wrap.")
            return
        abbr, ok = QInputDialog.getText(
            self, "Wrap with Abbreviation", "Abbreviation (e.g. div.wrapper  or  ul>li*):")
        if not ok or not abbr.strip():
            return
        line_start = text.rfind("\n", 0, s) + 1
        base = text[line_start:s]
        if base.strip():
            base = base[: len(base) - len(base.lstrip())]
        lines = text[s:e].split("\n")
        lines = [lines[0]] + [l[len(base):] if l.startswith(base) else l for l in lines[1:]]
        exp = markup.expand(abbr.strip(), "jsx" if self.language == "jsx" else "html", INDENT,
                            content="\n".join(lines))
        if exp is None:
            self._message(f"'{abbr}' is not a valid abbreviation.")
            return
        out, stops = indent_expansion(exp, base)
        self._insert_expansion(s, e, out, stops)

    def emmet_action(self, name, **kw):
        """Run a named Emmet action on the editor. Returns True if it did something."""
        if name == "expand":
            done = self.expand_abbreviation()
            if not done:
                self._message("No Emmet abbreviation before the cursor.")
            return done
        if name == "wrap":
            self.wrap_with_abbreviation()
            return True
        text, s, e = self._text_and_selection()
        lang = self._structure_language()
        edit = None
        if name == "balance_out":
            edit = tags.balance_outward(text, s, e, lang)
        elif name == "balance_in":
            edit = tags.balance_inward(text, s, e, lang)
        elif name == "pair":
            edit = tags.go_to_matching_pair(text, s, self.language)
        elif name == "toggle_comment":
            edit = actions.toggle_comment(text, s, e, self.language)
        elif name == "remove_tag" and lang == "html":
            edit = tags.remove_tag(text, s)
        elif name == "split_join" and lang == "html":
            edit = tags.split_join_tag(text, s)
        elif name == "merge_lines":
            edit = tags.merge_lines(text, s, e)
        elif name == "math":
            edit = actions.evaluate_math(text, s, e)
        elif name == "step":
            edit = actions.step_number(text, s, e, kw["delta"])
        elif name in ("next_point", "prev_point"):
            edit = tags.next_edit_point(text, s, forward=name == "next_point")
        elif name in ("next_item", "prev_item"):
            edit = tags.select_item(text, s, e, lang, forward=name == "next_item")
        elif name == "image_size":
            edit = actions.update_image_size(text, s, self._image_size)
        elif name == "encode_image":
            edit = actions.encode_image(text, s, self._read_image)
        if edit is None:
            self._message("Emmet: nothing to do here.")
            return False
        return self.apply_emmet_edit(edit)

    # ---- image helpers
    def _resolve_image(self, src):
        if not src or src.startswith(("http:", "https:", "data:", "//")):
            return None
        if os.path.isabs(src):
            return src
        if self.base_dir:
            return os.path.normpath(os.path.join(self.base_dir, src))
        return None

    def _image_size(self, src):
        path = self._resolve_image(src)
        if not path or not os.path.isfile(path):
            self._message("Can't find that image file (save the document first?).")
            return None
        size = QImageReader(path).size()
        return (size.width(), size.height()) if size.isValid() else None

    def _read_image(self, src):
        path = self._resolve_image(src)
        if not path or not os.path.isfile(path):
            self._message("Can't find that image file (save the document first?).")
            return None
        with open(path, "rb") as f:
            return actions.guess_mime(path), f.read()
