"""QPlainTextEdit with a line-number gutter, tuned for editing Python."""
import re

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QTextCursor, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from app.emmet.editor_support import EmmetMixin
from app.themes import CODE_THEMES, DEFAULT_CODE_THEME

OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}
CLOSE_TO_OPEN = {v: k for k, v in OPEN_TO_CLOSE.items()}
QUOTE_CHARS = {'"', "'"}
# Characters after which a typed quote is treated as the start of a new string
# (rather than a literal apostrophe, e.g. inside "it's" or a comment).
EXPR_START_CHARS = set(" \t([{,:=+-*/%<>!&|^~; ")

INDENT = "    "
PLAIN_LANGUAGES = {"text", "markdown"}
HTML_LIKE = {"html", "xml", "xsl", "jsx"}
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr", "!doctype",
}
OPEN_TAG_AT_END = re.compile(r"<([A-Za-z][\w:-]*)(?:\s[^<>]*)?>$")
OPEN_TAG_UNFINISHED = re.compile(r"<([A-Za-z][\w:-]*)(?:\s[^<>]*)?$")


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(EmmetMixin, QPlainTextEdit):
    emmet_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_emmet()
        self.setFont(QFont("Cascadia Mono", 11))
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.line_number_area = LineNumberArea(self)
        self.autocorrect_enabled = True
        self.language = "python"
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.line_highlight_color = QColor("#2a2d2e")
        self.gutter_bg_color = QColor("#1e1e1e")
        self.gutter_fg_color = QColor("#858585")

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.set_code_theme(CODE_THEMES[DEFAULT_CODE_THEME])

    def set_code_theme(self, theme: dict):
        """Style the editor itself so it ignores the app-wide theme."""
        self.line_highlight_color = QColor(theme["line_highlight"])
        self.gutter_bg_color = QColor(theme["gutter_bg"])
        self.gutter_fg_color = QColor(theme["gutter_fg"])
        self.setStyleSheet(
            "QPlainTextEdit {"
            f" background-color: {theme['background']}; color: {theme['foreground']};"
            f" selection-background-color: {theme['selection']}; selection-color: {theme['foreground']};"
            f" border: 1px solid {theme['line_highlight']}; }}"
        )
        self.highlight_current_line()
        self.line_number_area.update()

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(self.line_highlight_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), self.gutter_bg_color)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self.gutter_fg_color)
                painter.drawText(
                    0, int(top), self.line_number_area.width() - 6, self.fontMetrics().height(),
                    Qt.AlignRight, number,
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    # ---- optional coding autocorrect: bracket/quote pairing + smart indent ----
    def set_autocorrect_enabled(self, enabled: bool):
        self.autocorrect_enabled = enabled

    def set_language(self, language: str):
        self.language = language
        wrap = QPlainTextEdit.WidgetWidth if language in PLAIN_LANGUAGES else QPlainTextEdit.NoWrap
        self.setLineWrapMode(wrap)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Tab and not (event.modifiers() & Qt.ControlModifier):
            if self.emmet_tab():
                return
            self._indent_or_insert_spaces()
            return
        if key == Qt.Key_Escape and self._stops:
            self._clear_stops()
        if key == Qt.Key_Backtab:
            self._dedent_lines()
            return

        if not self.autocorrect_enabled or self.language in PLAIN_LANGUAGES:
            super().keyPressEvent(event)
            return

        text = event.text()
        cursor = self.textCursor()

        if key in (Qt.Key_Return, Qt.Key_Enter) and not cursor.hasSelection():
            self._insert_newline_with_indent()
            return

        if text == ">" and self.language in HTML_LIKE and not cursor.hasSelection() and self._autoclose_html_tag():
            return

        if key == Qt.Key_Backspace and not cursor.hasSelection() and self._collapse_pair_on_backspace():
            return

        if not cursor.hasSelection() and text in OPEN_TO_CLOSE:
            super().keyPressEvent(event)
            c = self.textCursor()
            c.insertText(OPEN_TO_CLOSE[text])
            c.movePosition(QTextCursor.Left)
            self.setTextCursor(c)
            return

        if not cursor.hasSelection() and (text in CLOSE_TO_OPEN or text in QUOTE_CHARS):
            if self._char_at_cursor(cursor) == text:
                cursor.movePosition(QTextCursor.Right)
                self.setTextCursor(cursor)
                return
            if text in QUOTE_CHARS and self._is_expr_start(cursor):
                super().keyPressEvent(event)
                c = self.textCursor()
                c.insertText(text)
                c.movePosition(QTextCursor.Left)
                self.setTextCursor(c)
                return

        super().keyPressEvent(event)

    def _char_at_cursor(self, cursor) -> str:
        pos = cursor.position()
        if pos >= self.document().characterCount() - 1:
            return ""
        return self.document().characterAt(pos)

    def _is_expr_start(self, cursor) -> bool:
        pos = cursor.position()
        if pos == 0:
            return True
        prev_char = self.document().characterAt(pos - 1)
        return prev_char in EXPR_START_CHARS

    def _collapse_pair_on_backspace(self) -> bool:
        cursor = self.textCursor()
        pos = cursor.position()
        if pos == 0 or pos >= self.document().characterCount() - 1:
            return False
        prev_char = self.document().characterAt(pos - 1)
        next_char = self.document().characterAt(pos)
        is_bracket_pair = prev_char in OPEN_TO_CLOSE and next_char == OPEN_TO_CLOSE[prev_char]
        is_quote_pair = prev_char in QUOTE_CHARS and next_char == prev_char
        if not (is_bracket_pair or is_quote_pair):
            return False
        cursor.deleteChar()
        cursor.deletePreviousChar()
        self.setTextCursor(cursor)
        return True

    def _insert_newline_with_indent(self):
        cursor = self.textCursor()
        line = cursor.block().text()
        prefix = line[: cursor.positionInBlock()]
        suffix = line[cursor.positionInBlock():]
        indent = re.match(r"[ \t]*", prefix).group(0)
        stripped = prefix.rstrip()

        if self.language == "python":
            extra = INDENT if stripped.endswith(":") else ""
            cursor.insertText("\n" + indent + extra)
            self.setTextCursor(cursor)
            return

        opens_block = bool(stripped) and stripped[-1] in "{[("
        if not opens_block and self.language in HTML_LIKE:
            m = OPEN_TAG_AT_END.search(stripped)
            opens_block = bool(m) and m.group(1).lower() not in VOID_TAGS and not stripped.endswith("/>")
            closes_here = suffix.lstrip().startswith("</")
        else:
            closes_here = suffix.lstrip()[:1] in ("}", "]", ")") if suffix.strip() else False

        if opens_block and closes_here:
            cursor.insertText("\n" + indent + INDENT + "\n" + indent)
            cursor.movePosition(QTextCursor.Up)
            cursor.movePosition(QTextCursor.EndOfLine)
        else:
            cursor.insertText("\n" + indent + (INDENT if opens_block else ""))
        self.setTextCursor(cursor)

    def _autoclose_html_tag(self) -> bool:
        cursor = self.textCursor()
        prefix = cursor.block().text()[: cursor.positionInBlock()]
        if prefix.endswith("/"):
            return False
        m = OPEN_TAG_UNFINISHED.search(prefix)
        if not m:
            return False
        tag = m.group(1)
        cursor.insertText(">")
        if tag.lower() not in VOID_TAGS:
            cursor.insertText(f"</{tag}>")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(tag) + 3)
        self.setTextCursor(cursor)
        return True

    # ---- Tab / Shift+Tab (always spaces, so files never mix tabs and spaces) ----
    def _indent_or_insert_spaces(self):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.insertText(INDENT)
            return
        self._for_selected_blocks(lambda c: c.insertText(INDENT))

    def _dedent_lines(self):
        def dedent(c):
            text = c.block().text()
            remove = 0
            while remove < len(INDENT) and remove < len(text) and text[remove] == " ":
                remove += 1
            if remove == 0 and text.startswith("\t"):
                remove = 1
            for _ in range(remove):
                c.deleteChar()

        self._for_selected_blocks(dedent)

    def _for_selected_blocks(self, action):
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        doc = self.document()
        first = doc.findBlock(start)
        last = doc.findBlock(max(start, end - 1)) if end > start else first
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        block = first
        while block.isValid() and block.blockNumber() <= last.blockNumber():
            edit.setPosition(block.position())
            action(edit)
            block = block.next()
        edit.endEditBlock()
