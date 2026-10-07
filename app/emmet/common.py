"""Shared types for the Emmet engine (pure Python, no Qt)."""
from dataclasses import dataclass, field


@dataclass
class Expansion:
    """Result of expanding an abbreviation.

    text  - the expanded text (newlines are "\\n", indented with the requested unit)
    stops - tab stops in visiting order, as (start, end) offsets into text; a stop
            with start == end is a bare cursor position, otherwise the range is
            a placeholder that gets selected.
    """
    text: str
    stops: list = field(default_factory=list)


@dataclass
class Edit:
    """A text edit: replace text[start:end] with `text`, then select sel_start..sel_end.

    Selection offsets refer to the document *after* the edit is applied.
    """
    start: int
    end: int
    text: str
    sel_start: int
    sel_end: int


class EmmetError(Exception):
    pass
