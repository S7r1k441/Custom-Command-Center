"""A built-in Emmet reference dialog: abbreviation syntax and every editor shortcut."""
from PySide6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout

# (menu label, shortcut, action name, extra kwargs) - shared with the Emmet menu.
EMMET_ACTIONS = [
    ("Expand Abbreviation", "Ctrl+E", "expand", {}),
    ("Wrap with Abbreviation...", "Ctrl+Alt+W", "wrap", {}),
    ("Balance (Outward)", "Ctrl+Shift+D", "balance_out", {}),
    ("Balance (Inward)", "Ctrl+Alt+D", "balance_in", {}),
    ("Go to Matching Pair", "Ctrl+Shift+\\", "pair", {}),
    ("Toggle Comment", "Ctrl+/", "toggle_comment", {}),
    ("Remove Tag", "Ctrl+Alt+K", "remove_tag", {}),
    ("Split / Join Tag", "Ctrl+Alt+J", "split_join", {}),
    ("Merge Lines", "Ctrl+Alt+M", "merge_lines", {}),
    ("Evaluate Math Expression", "Ctrl+Shift+Y", "math", {}),
    ("Increment Number by 1", "Alt+Up", "step", {"delta": 1}),
    ("Decrement Number by 1", "Alt+Down", "step", {"delta": -1}),
    ("Increment Number by 0.1", "Ctrl+Alt+Up", "step", {"delta": 0.1}),
    ("Decrement Number by 0.1", "Ctrl+Alt+Down", "step", {"delta": -0.1}),
    ("Increment Number by 10", "Shift+Alt+Up", "step", {"delta": 10}),
    ("Decrement Number by 10", "Shift+Alt+Down", "step", {"delta": -10}),
    ("Next Edit Point", "Alt+Right", "next_point", {}),
    ("Previous Edit Point", "Alt+Left", "prev_point", {}),
    ("Select Next Item", "Ctrl+.", "next_item", {}),
    ("Select Previous Item", "Ctrl+,", "prev_item", {}),
    ("Update Image Size", "Ctrl+Alt+I", "image_size", {}),
    ("Encode Image to data: URL", "Ctrl+Alt+E", "encode_image", {}),
]

SYNTAX = [
    ("div", "an element (empty tags get a cursor stop)"),
    ("ul>li", "child: li inside ul"),
    ("h1+p", "sibling: p after h1"),
    ("div>p>span^p", "climb up: p after the div's first child"),
    ("(header>h1)+main", "grouping"),
    ("li*3", "repeat 3 times"),
    ("li.item$*3", "numbering: item1, item2, item3 ($$ pads: 01; $@- counts down; $@3 starts at 3)"),
    ("#page.wrap.big", "id and classes (div is implied)"),
    ("a[href=# title='x y']", "attributes (quote values with spaces; name. makes a boolean attribute)"),
    ("p{Hello}", "text content"),
    ("ul>.item*2", "implicit tag names: li inside ul, td inside tr, option inside select, span inside p"),
    ("!  or  html:5", "full HTML5 document (also html:4t, html:4s, html:xt, html:xs, html:xxs, doc)"),
    ("lorem20  or  p>lorem", "placeholder text (loremN = N words)"),
    ("li.a$*2|c", "filters: |c adds comments, |e escapes the output as HTML"),
    ("a:link  a:mail  a:tel  a:blank", "link snippets"),
    ("input:email  input:submit  input:checkbox", "form snippets (input:text/password/date/number/file/radio/...)"),
    ("btn:s  fieldset:d  select+  table+  ul+", "button/disabled/expando snippets"),
    ("bq  fig  figc  sect  art  hdr  ftr  nav  mn  det  sum", "short aliases for common tags"),
    ("meta:vp  link:css  link:favicon  script:src  img:sizes", "head and media snippets"),
]

CSS = [
    ("m10  m10-20  m-a  m-10  mt0", "margin (10px, 10px 20px, auto, -10px); mt/mr/mb/ml and p, pt, pr, pb, pl likewise"),
    ("w100p  h50vh  w1.5e  maw200  mih1r", "sizes: p = %, e = em, x = ex, or any unit (vh, rem, ...)"),
    ("df  dn  db  di  dib  dg", "display: flex / none / block / inline / inline-block / grid"),
    ("posa  posr  posf  pos:s", "position absolute / relative / fixed / static"),
    ("fz14  fw700  fwb  lh1.5  ff  ta:c  tac  tdn  ttu", "text and font"),
    ("c#f00  c#fc0  bgc#e0  c#0  bgc#fc0.5", "colors: #f -> #fff, #e0 -> #e0e0e0, #0 -> #000, hex.alpha -> rgba()"),
    ("bd  bdrs5  bdt  bxsh  bxz  op.5  z10", "border, radius, shadow, box-sizing, opacity, z-index"),
    ("jcc  jcsb  aic  aifs  fxd  fxdc  fxw", "flexbox: justify-content, align-items, flex-direction, wrap"),
    ("bg  bgi  bgr  bgs  bgp", "background properties"),
    ("trs  trf  anim  -trs  -wm-trs", "transition, transform, animation; a leading - adds vendor prefixes (-w- webkit, -m- moz, -s- ms, -o- opera)"),
    ("m10!  !", "adds !important"),
    ("p10+m20", "several declarations at once"),
    ("lg(to right, #f00, #0)", "linear-gradient (also rg(...))"),
    ("@m  @kf  @f  @i  @c", "at-rules: @media, @keyframes, @font-face, @import, @charset"),
]


def _rows(items):
    return "".join(f"<tr><td><b>{a}</b></td><td>{b}</td></tr>" for a, b in items)


def cheat_sheet_html():
    shortcuts = "".join(
        f"<tr><td><b>{label}</b></td><td>{key}</td></tr>" for label, key, _, _ in EMMET_ACTIONS)
    return f"""
    <h2>Emmet cheat sheet</h2>
    <p>Type an abbreviation and press <b>Tab</b> (or Ctrl+E). Tab again jumps to the next
    cursor stop. Works in HTML, XML/XSL, JSX/TSX, Pug, HAML, Slim, CSS/SCSS/Less, Sass and
    Stylus files, and inside &lt;style&gt; blocks in HTML.</p>
    <h3>Markup abbreviations</h3><table cellpadding="4">{_rows(SYNTAX)}</table>
    <h3>CSS abbreviations</h3><table cellpadding="4">{_rows(CSS)}</table>
    <h3>Editor shortcuts (Emmet menu)</h3><table cellpadding="4">{shortcuts}</table>
    <p>Tab / Shift+Tab also indent and dedent the selected lines.</p>
    """


class EmmetCheatSheet(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Emmet Cheat Sheet")
        self.resize(760, 640)
        view = QTextBrowser()
        view.setHtml(cheat_sheet_html())
        layout = QVBoxLayout(self)
        layout.addWidget(view)
