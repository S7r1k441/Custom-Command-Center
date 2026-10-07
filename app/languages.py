"""File-type detection: which editor and syntax highlighting a file gets."""
import os

_HTML_EXTENSIONS = (
    ".html .htm .xhtml .shtml .php .phtml .vue .svelte .ejs .erb .hbs .handlebars .mustache "
    ".jinja .jinja2 .j2 .twig .njk .liquid .jsp .asp .aspx .cshtml .tpl .blade"
).split()
_XML_EXTENSIONS = ".xml .svg .rss .atom .xaml .plist .csproj .config .kml".split()

EXT_TO_LANGUAGE = {
    ".py": "python", ".pyw": "python",
    ".css": "css", ".scss": "css", ".less": "css",
    ".sass": "sass",
    ".styl": "stylus", ".stylus": "stylus",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".ts": "javascript",
    ".jsx": "jsx", ".tsx": "jsx",
    ".json": "json",
    ".md": "markdown", ".markdown": "markdown",
    ".xsl": "xsl", ".xslt": "xsl",
    ".pug": "pug", ".jade": "pug",
    ".haml": "haml",
    ".slim": "slim",
}
EXT_TO_LANGUAGE.update({ext: "html" for ext in _HTML_EXTENSIONS})
EXT_TO_LANGUAGE.update({ext: "xml" for ext in _XML_EXTENSIONS})

LANGUAGE_LABELS = {
    "python": "Python",
    "html": "HTML",
    "xml": "XML",
    "xsl": "XSL",
    "css": "CSS / SCSS / Less",
    "sass": "Sass",
    "stylus": "Stylus",
    "javascript": "JavaScript",
    "jsx": "JSX / TSX",
    "json": "JSON",
    "markdown": "Markdown",
    "pug": "Pug",
    "haml": "HAML",
    "slim": "Slim",
    "text": "Plain text",
}

# Languages that can be previewed in the browser.
PREVIEW_LANGUAGES = {"html", "xml"}

# Files that are not text: opened with the system's default app instead.
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".pdf", ".zip",
    ".exe", ".dll", ".mp3", ".mp4", ".wav", ".avi", ".mov", ".docx", ".xlsx",
    ".pptx", ".7z", ".rar", ".pyc",
}

WORD_WRAP_LANGUAGES = {"text", "markdown"}


def detect_language(path: str | None) -> str:
    if not path:
        return "text"
    return EXT_TO_LANGUAGE.get(os.path.splitext(path)[1].lower(), "text")


def is_binary_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in BINARY_EXTENSIONS
