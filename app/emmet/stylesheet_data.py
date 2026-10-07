"""Static data for CSS abbreviation expansion."""

# abbreviation -> "property" or "property|default value"
_SNIPPETS = """
ai align-items
ac align-content
as align-self
anim animation
animdel animation-delay
animdir animation-direction
animdur animation-duration
animfm animation-fill-mode
animic animation-iteration-count
animn animation-name
animps animation-play-state
animtf animation-timing-function
ap appearance
b bottom
bd border|1px solid #000
bdb border-bottom|1px solid #000
bdbc border-bottom-color|#000
bdbs border-bottom-style
bdbw border-bottom-width
bdblrs border-bottom-left-radius
bdbrrs border-bottom-right-radius
bdc border-color|#000
bdcl border-collapse
bdi border-image
bdl border-left|1px solid #000
bdlc border-left-color|#000
bdls border-left-style
bdlw border-left-width
bdr border-right|1px solid #000
bdrc border-right-color|#000
bdrs border-radius
bdrst border-right-style
bdrw border-right-width
bds border-style|solid
bdsp border-spacing
bdt border-top|1px solid #000
bdtc border-top-color|#000
bdtlrs border-top-left-radius
bdtrrs border-top-right-radius
bdts border-top-style
bdtw border-top-width
bdw border-width
bfv backface-visibility
bg background|#000
bga background-attachment
bgbm background-blend-mode
bgc background-color|#fff
bgcp background-clip
bgi background-image|url()
bgo background-origin
bgp background-position
bgpx background-position-x
bgpy background-position-y
bgr background-repeat
bgs background-size
bgsz background-size
bxsh box-shadow|0 0 5px #000
bxz box-sizing|border-box
bxsz box-sizing|border-box
c color|#000
cl clear
cnt content|''
coi counter-increment
colm columns
colmc column-count
colmf column-fill
colmg column-gap
colmr column-rule
colms column-span
colmw column-width
cor counter-reset
cp clip
cps caption-side
cur cursor|pointer
d display
ec empty-cells
f font
ff font-family
fl float
fs font-style
fsm font-smooth
fst font-stretch
fv font-variant
fw font-weight
fx flex
fxb flex-basis
fxd flex-direction
fxf flex-flow
fxg flex-grow
fxsh flex-shrink
fxw flex-wrap
fz font-size
fza font-size-adjust
gap gap
gtc grid-template-columns
gtr grid-template-rows
gta grid-template-areas
gc grid-column
gr grid-row
gcg column-gap
grg row-gap
h height
jc justify-content
ji justify-items
js justify-self
l left
lh line-height
lis list-style
lisi list-style-image
lisp list-style-position
list list-style-type
lts letter-spacing
m margin
mah max-height
maw max-width
mb margin-bottom
mih min-height
miw min-width
ml margin-left
mr margin-right
mt margin-top
mbm mix-blend-mode
ol outline
olc outline-color|#000
olo outline-offset
ols outline-style
olw outline-width
op opacity
ord order
orp orphans
ov overflow
ovs overflow-style
ovx overflow-x
ovy overflow-y
p padding
pb padding-bottom
pe pointer-events
pgba page-break-after
pgbb page-break-before
pgbi page-break-inside
pl padding-left
pos position
pr padding-right
pt padding-top
q quotes
r right
rsz resize
t top
ta text-align
tal text-align-last
tbl table-layout
td text-decoration
te text-emphasis
ti text-indent
tj text-justify
tov text-overflow
trf transform
trfo transform-origin
trfs transform-style
trs transition
trsde transition-delay
trsdu transition-duration
trsp transition-property
trstf transition-timing-function
ts text-shadow|1px 1px 1px #000
tt text-transform
tw text-wrap
us user-select
v visibility
va vertical-align
w width
whs white-space
wid widows
wm writing-mode
wob word-break
wos word-spacing
wow word-wrap
z z-index
zoom zoom
objf object-fit
objp object-position
fil filter
bdf backdrop-filter
asr aspect-ratio
tsz tab-size
wc will-change
scb scroll-behavior
txa text-align
"""

SNIPPETS = {}
for _line in _SNIPPETS.strip().splitlines():
    _abbr, _rest = _line.split(" ", 1)
    _prop, _, _default = _rest.partition("|")
    SNIPPETS[_abbr] = (_prop, _default or None)

# Properties that take plain numbers instead of "px".
UNITLESS = {
    "line-height", "opacity", "z-index", "font-weight", "zoom", "flex", "flex-grow",
    "flex-shrink", "order", "orphans", "widows", "column-count", "fill-opacity",
    "stroke-opacity", "animation-iteration-count", "counter-increment", "counter-reset",
    "tab-size", "font-size-adjust", "grid-column", "grid-row", "aspect-ratio",
}

UNIT_ALIASES = {"p": "%", "e": "em", "x": "ex"}
UNITS = {
    "px", "em", "rem", "ex", "ch", "vw", "vh", "vmin", "vmax", "pt", "pc", "cm", "mm",
    "in", "s", "ms", "deg", "rad", "grad", "turn", "fr", "dpi", "dppx", "%", "q",
    "cqw", "cqh", "svh", "lvh", "dvh", "svw", "lvw", "dvw",
}

_GLOBAL_KEYWORDS = "inherit initial unset revert"
_ALIGN = "center flex-start flex-end space-between space-around space-evenly start end stretch baseline"

# property -> keywords, most common first (abbreviations resolve to the first match)
KEYWORDS = {
    "position": "relative absolute fixed static sticky",
    "display": "block inline inline-block flex inline-flex grid inline-grid none table table-cell "
               "table-row table-column table-caption table-header-group table-footer-group "
               "table-column-group list-item contents flow-root run-in",
    "float": "left right none inline-start inline-end",
    "clear": "both left right none",
    "overflow": "hidden auto scroll visible clip",
    "overflow-x": "hidden auto scroll visible clip",
    "overflow-y": "hidden auto scroll visible clip",
    "visibility": "hidden visible collapse",
    "cursor": "pointer auto default text move not-allowed crosshair help wait progress grab "
              "grabbing zoom-in zoom-out copy alias context-menu cell no-drop none",
    "text-align": "left center right justify start end",
    "text-align-last": "left center right justify start end auto",
    "text-decoration": "none underline line-through overline",
    "text-transform": "uppercase capitalize lowercase none full-width",
    "text-overflow": "ellipsis clip",
    "font-weight": "bold normal bolder lighter 100 200 300 400 500 600 700 800 900",
    "font-style": "italic normal oblique",
    "font-variant": "small-caps normal",
    "font-family": "sans-serif serif monospace cursive fantasy system-ui Arial Helvetica Georgia "
                   "Verdana Tahoma Times",
    "white-space": "nowrap normal pre pre-wrap pre-line break-spaces",
    "word-wrap": "break-word normal",
    "word-break": "break-all normal keep-all break-word",
    "vertical-align": "top middle bottom baseline text-top text-bottom sub super",
    "box-sizing": "border-box content-box",
    "background-repeat": "no-repeat repeat repeat-x repeat-y space round",
    "background-size": "cover contain auto",
    "background-position": "center top bottom left right",
    "background-attachment": "fixed scroll local",
    "background-clip": "border-box padding-box content-box text",
    "background-origin": "padding-box border-box content-box",
    "border-style": "solid dashed dotted double none hidden groove ridge inset outset",
    "border-top-style": "solid dashed dotted double none hidden",
    "border-right-style": "solid dashed dotted double none hidden",
    "border-bottom-style": "solid dashed dotted double none hidden",
    "border-left-style": "solid dashed dotted double none hidden",
    "outline-style": "solid dashed dotted double none auto",
    "border-collapse": "collapse separate",
    "table-layout": "fixed auto",
    "list-style": "none disc circle square decimal inside outside",
    "list-style-type": "none disc circle square decimal lower-alpha upper-alpha lower-roman upper-roman",
    "list-style-position": "inside outside",
    "flex-direction": "row column row-reverse column-reverse",
    "flex-wrap": "wrap nowrap wrap-reverse",
    "justify-content": _ALIGN + " left right",
    "justify-items": _ALIGN + " left right",
    "justify-self": "auto " + _ALIGN,
    "align-items": _ALIGN,
    "align-content": _ALIGN,
    "align-self": "auto " + _ALIGN,
    "resize": "none both horizontal vertical",
    "user-select": "none auto text all contain",
    "pointer-events": "none auto all",
    "object-fit": "cover contain fill none scale-down",
    "opacity": "",
    "transition-timing-function": "ease ease-in ease-out ease-in-out linear step-start step-end",
    "animation-timing-function": "ease ease-in ease-out ease-in-out linear step-start step-end",
    "animation-direction": "normal reverse alternate alternate-reverse",
    "animation-fill-mode": "none forwards backwards both",
    "animation-play-state": "running paused",
    "animation-iteration-count": "infinite",
    "backface-visibility": "hidden visible",
    "transform-style": "flat preserve-3d",
    "writing-mode": "horizontal-tb vertical-rl vertical-lr",
    "appearance": "none auto",
    "scroll-behavior": "smooth auto",
    "mix-blend-mode": "multiply screen overlay darken lighten normal",
    "empty-cells": "show hide",
    "caption-side": "top bottom",
    "quotes": "none auto",
    "content": "none normal",
    "margin": "auto",
    "margin-top": "auto", "margin-right": "auto", "margin-bottom": "auto", "margin-left": "auto",
    "width": "auto", "height": "auto", "top": "auto", "right": "auto", "bottom": "auto", "left": "auto",
    "max-width": "none", "max-height": "none", "min-width": "auto", "min-height": "auto",
    "z-index": "auto", "line-height": "normal", "letter-spacing": "normal", "word-spacing": "normal",
    "clip": "auto", "flex-basis": "auto content", "flex": "auto none", "order": "",
    "column-count": "auto", "column-gap": "normal", "gap": "normal",
}

DEFAULT_VALUES = {
    "position": "relative", "display": "block", "float": "left", "clear": "both",
    "overflow": "hidden", "overflow-x": "hidden", "overflow-y": "hidden", "visibility": "hidden",
    "text-align": "left", "text-decoration": "none", "text-transform": "uppercase",
    "font-weight": "bold", "font-style": "italic", "white-space": "nowrap",
    "vertical-align": "top", "text-overflow": "ellipsis", "background-repeat": "no-repeat",
    "background-size": "cover", "cursor": "pointer", "list-style": "none",
    "flex-direction": "column", "justify-content": "center", "align-items": "center",
    "align-content": "center", "user-select": "none", "resize": "none",
    "word-wrap": "break-word", "word-break": "break-all",
}

PREFIXES = {"w": "-webkit-", "m": "-moz-", "s": "-ms-", "o": "-o-"}

PROPERTIES = """
align-content align-items align-self all animation animation-delay animation-direction
animation-duration animation-fill-mode animation-iteration-count animation-name
animation-play-state animation-timing-function appearance aspect-ratio backdrop-filter
backface-visibility background background-attachment background-blend-mode background-clip
background-color background-image background-origin background-position background-position-x
background-position-y background-repeat background-size border border-bottom
border-bottom-color border-bottom-left-radius border-bottom-right-radius border-bottom-style
border-bottom-width border-collapse border-color border-image border-left border-left-color
border-left-style border-left-width border-radius border-right border-right-color
border-right-style border-right-width border-spacing border-style border-top border-top-color
border-top-left-radius border-top-right-radius border-top-style border-top-width border-width
bottom box-shadow box-sizing caption-side caret-color clear clip clip-path color column-count
column-fill column-gap column-rule column-rule-color column-rule-style column-rule-width
column-span column-width columns content counter-increment counter-reset cursor direction
display empty-cells fill filter flex flex-basis flex-direction flex-flow flex-grow flex-shrink
flex-wrap float font font-family font-feature-settings font-kerning font-size font-size-adjust
font-stretch font-style font-variant font-weight gap grid grid-area grid-auto-columns
grid-auto-flow grid-auto-rows grid-column grid-column-end grid-column-start grid-gap grid-row
grid-row-end grid-row-start grid-template grid-template-areas grid-template-columns
grid-template-rows hanging-punctuation height hyphens image-rendering isolation justify-content
justify-items justify-self left letter-spacing line-height list-style list-style-image
list-style-position list-style-type margin margin-bottom margin-left margin-right margin-top
mask max-height max-width min-height min-width mix-blend-mode object-fit object-position
opacity order orphans outline outline-color outline-offset outline-style outline-width
overflow overflow-wrap overflow-x overflow-y padding padding-bottom padding-left padding-right
padding-top page-break-after page-break-before page-break-inside perspective perspective-origin
place-content place-items place-self pointer-events position quotes resize right row-gap
scroll-behavior scroll-margin scroll-padding scroll-snap-align scroll-snap-type shape-outside
stroke stroke-width tab-size table-layout text-align text-align-last text-decoration
text-decoration-color text-decoration-line text-decoration-style text-indent text-justify
text-overflow text-shadow text-transform top transform transform-origin transform-style
transition transition-delay transition-duration transition-property transition-timing-function
unicode-bidi user-select vertical-align visibility white-space widows width will-change
word-break word-spacing word-wrap writing-mode z-index zoom
""".split()
