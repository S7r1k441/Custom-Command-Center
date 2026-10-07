"""Static data for HTML/XML abbreviation expansion."""

INLINE_ELEMENTS = {
    "a", "abbr", "acronym", "applet", "b", "basefont", "bdo", "big", "br", "button",
    "cite", "code", "del", "dfn", "em", "font", "i", "iframe", "img", "input", "ins",
    "kbd", "label", "map", "object", "q", "s", "samp", "select", "small", "span",
    "strike", "strong", "sub", "sup", "textarea", "tt", "u", "var",
}

VOID_ELEMENTS = {
    "area", "base", "basefont", "br", "col", "command", "embed", "frame", "hr", "img",
    "input", "isindex", "keygen", "link", "meta", "param", "source", "track", "wbr",
}

BOOLEAN_ATTRS = {
    "allowfullscreen", "async", "autofocus", "autoplay", "checked", "controls",
    "default", "defer", "disabled", "formnovalidate", "hidden", "ismap", "itemscope",
    "loop", "multiple", "muted", "nomodule", "novalidate", "open", "readonly",
    "required", "reversed", "selected",
}

# Tag used for an element written without a name (".item", "#x", "[a=b]"),
# chosen by the parent tag.
IMPLICIT_CHILD = {
    "ul": "li", "ol": "li", "menu": "li",
    "table": "tr", "tbody": "tr", "thead": "tr", "tfoot": "tr",
    "tr": "td", "colgroup": "col",
    "select": "option", "optgroup": "option", "datalist": "option",
    "audio": "source", "video": "source", "object": "param", "map": "area",
    "dl": "dt",
}
IMPLICIT_SPAN_PARENTS = {
    "p", "a", "abbr", "acronym", "b", "bdo", "big", "blockquote", "button", "cite",
    "code", "dfn", "em", "font", "h1", "h2", "h3", "h4", "h5", "h6", "i", "ins",
    "kbd", "label", "q", "s", "samp", "small", "span", "strike", "strong", "sub",
    "sup", "tt", "u", "var", "legend", "caption", "figcaption", "summary",
}

VARIABLES = {"lang": "en", "charset": "UTF-8"}

DOCTYPES = {
    "": "<!DOCTYPE html>",
    "5": "<!DOCTYPE html>",
    "4t": '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">',
    "4s": '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">',
    "xt": '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
    "xs": '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
    "xxs": '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">',
    "xml": '<?xml version="1.0" encoding="UTF-8"?>',
}

# Whole-document abbreviations. {P} is one indent unit.
DOCUMENTS = {
    "!": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n{P}<meta charset=\"UTF-8\">\n"
         "{P}<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
         "{P}<title>Document</title>\n</head>\n<body>\n{P}${0}\n</body>\n</html>",
    "html:5": None,       # same as "!"
    "doc": "<html lang=\"en\">\n<head>\n{P}<meta charset=\"UTF-8\">\n{P}<title>Document</title>\n</head>\n"
           "<body>\n{P}${0}\n</body>\n</html>",
    "doc4": "<html lang=\"en\">\n<head>\n{P}<meta http-equiv=\"Content-Type\" content=\"text/html;charset=UTF-8\">\n"
            "{P}<title>Document</title>\n</head>\n<body>\n{P}${0}\n</body>\n</html>",
    "html:4t": "{DT4T}\n<html lang=\"en\">\n<head>\n{P}<meta http-equiv=\"Content-Type\" content=\"text/html;charset=UTF-8\">\n"
               "{P}<title>Document</title>\n</head>\n<body>\n{P}${0}\n</body>\n</html>",
    "html:4s": "{DT4S}\n<html lang=\"en\">\n<head>\n{P}<meta http-equiv=\"Content-Type\" content=\"text/html;charset=UTF-8\">\n"
               "{P}<title>Document</title>\n</head>\n<body>\n{P}${0}\n</body>\n</html>",
    "html:xt": "{DTXT}\n<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\">\n<head>\n"
               "{P}<meta http-equiv=\"Content-Type\" content=\"text/html;charset=UTF-8\">\n"
               "{P}<title>Document</title>\n</head>\n<body>\n{P}${0}\n</body>\n</html>",
    "html:xs": "{DTXS}\n<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\">\n<head>\n"
               "{P}<meta http-equiv=\"Content-Type\" content=\"text/html;charset=UTF-8\">\n"
               "{P}<title>Document</title>\n</head>\n<body>\n{P}${0}\n</body>\n</html>",
    "html:xxs": "{DTXXS}\n<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\">\n<head>\n"
                "{P}<meta http-equiv=\"Content-Type\" content=\"text/html;charset=UTF-8\">\n"
                "{P}<title>Document</title>\n</head>\n<body>\n{P}${0}\n</body>\n</html>",
}
DOCUMENTS["html:5"] = DOCUMENTS["!"]
DOCUMENT_DOCTYPE_KEYS = {"{DT4T}": "4t", "{DT4S}": "4s", "{DTXT}": "xt", "{DTXS}": "xs", "{DTXXS}": "xxs"}

_RAW_SNIPPETS = {
    "a": "a[href]",
    "a:blank": "a[href='http://${0}' target='_blank' rel='noopener noreferrer']",
    "a:link": "a[href='http://${0}']",
    "a:mail": "a[href='mailto:${0}']",
    "a:tel": "a[href='tel:+${0}']",
    "abbr": "abbr[title]",
    "acr|acronym": "acronym[title]",
    "base": "base[href]/",
    "basefont": "basefont/",
    "br": "br/",
    "frame": "frame/",
    "hr": "hr/",
    "bdo": "bdo[dir]",
    "bdo:r": "bdo[dir=rtl]",
    "bdo:l": "bdo[dir=ltr]",
    "col": "col/",
    "link": "link[rel=stylesheet href]/",
    "link:css": "link[href='${1:style}.css']",
    "link:print": "link[href='${1:print}.css' media=print]",
    "link:favicon": "link[rel='shortcut icon' type=image/x-icon href='${1:favicon.ico}']",
    "link:mf|link:manifest": "link[rel='manifest' href='${1:manifest.json}']",
    "link:touch": "link[rel=apple-touch-icon href='${1:favicon.png}']",
    "link:rss": "link[rel=alternate type=application/rss+xml title=RSS href='${1:rss.xml}']",
    "link:atom": "link[rel=alternate type=application/atom+xml title=Atom href='${1:atom.xml}']",
    "link:im|link:import": "link[rel=import href='${1:component}.html']",
    "meta": "meta/",
    "meta:utf": "meta[http-equiv=Content-Type content='text/html;charset=UTF-8']",
    "meta:vp": "meta[name=viewport content='width=${1:device-width}, initial-scale=${2:1.0}']",
    "meta:compat": "meta[http-equiv=X-UA-Compatible content='${1:IE=7}']",
    "meta:edge": "meta:compat[content='${1:ie=edge}']",
    "meta:redirect": "meta[http-equiv=refresh content='0; url=${1:http://example.com}']",
    "meta:refresh": "meta[http-equiv=refresh content='${1:5}']",
    "meta:kw": "meta[name=keywords content]",
    "meta:desc": "meta[name=description content]",
    "style": "style",
    "script": "script[!src]",
    "script:src": "script[src]",
    "img": "img[src alt]/",
    "img:s|img:srcset": "img[srcset src alt]",
    "img:z|img:sizes": "img[sizes srcset src alt]",
    "picture|pic": "picture",
    "src|source": "source/",
    "src:sc|source:src": "source[src type]",
    "src:s|source:srcset": "source[srcset]",
    "src:t|source:type": "source[srcset type='${1:image/}']",
    "src:z|source:sizes": "source[sizes srcset]",
    "src:m|source:media": "source[media='(${1:min-width: })' srcset]",
    "src:mt|source:media:type": "source:m[type='${2:image/}']",
    "src:mz|source:media:sizes": "source:m[sizes srcset]",
    "src:zt|source:sizes:type": "source[sizes srcset type='${1:image/}']",
    "iframe|ifr": "iframe[src frameborder=0]",
    "embed|emb": "embed[src type]/",
    "object|obj": "object[data type]",
    "param": "param[name value]/",
    "map": "map[name]",
    "area": "area[shape coords href alt]/",
    "area:d": "area[shape=default]",
    "area:c": "area[shape=circle]",
    "area:r": "area[shape=rect]",
    "area:p": "area[shape=poly]",
    "form": "form[action]",
    "form:get": "form[method=get]",
    "form:post": "form[method=post]",
    "label": "label[for]",
    "input": "input[type=${1:text}]/",
    "inp": "input[name=${1} id=${1}]",
    "input:h|input:hidden": "input[type=hidden name]",
    "input:t|input:text": "inp[type=text]",
    "input:search": "inp[type=search]",
    "input:email": "inp[type=email]",
    "input:url": "inp[type=url]",
    "input:p|input:password": "inp[type=password]",
    "input:datetime": "inp[type=datetime]",
    "input:date": "inp[type=date]",
    "input:datetime-local": "inp[type=datetime-local]",
    "input:month": "inp[type=month]",
    "input:week": "inp[type=week]",
    "input:time": "inp[type=time]",
    "input:tel": "inp[type=tel]",
    "input:number": "inp[type=number]",
    "input:color": "inp[type=color]",
    "input:c|input:checkbox": "inp[type=checkbox]",
    "input:r|input:radio": "inp[type=radio]",
    "input:range": "inp[type=range]",
    "input:f|input:file": "inp[type=file]",
    "input:s|input:submit": "input[type=submit value]",
    "input:i|input:image": "input[type=image src alt]",
    "input:b|input:btn|input:button": "input[type=button value]",
    "input:reset": "input:button[type=reset]",
    "isindex": "isindex/",
    "select": "select[name=${1} id=${1}]",
    "select:d|select:disabled": "select[disabled.]",
    "opt|option": "option[value]",
    "textarea|tarea": "textarea[name=${1} id=${1} cols=${2:30} rows=${3:10}]",
    "marquee": "marquee[behavior direction]",
    "menu:c|menu:context": "menu[type=context]>",
    "menu:t|menu:toolbar": "menu[type=toolbar]>",
    "video": "video[src]",
    "audio": "audio[src]",
    "html:xml": "html[xmlns=http://www.w3.org/1999/xhtml]",
    "keygen|kg": "keygen/",
    "command|cmd": "command/",
    "btn:s|button:s|button:submit|btn:submit": "button[type=submit]",
    "btn:r|button:r|button:reset|btn:reset": "button[type=reset]",
    "btn:d|button:d|button:disabled|btn:disabled": "button[disabled.]",
    "fst:d|fset:d|fieldset:d|fieldset:disabled|fst:disabled": "fieldset[disabled.]",
    "bq": "blockquote",
    "fig": "figure",
    "figc": "figcaption",
    "cap": "caption",
    "colg": "colgroup",
    "fst|fset": "fieldset",
    "btn": "button",
    "optg": "optgroup",
    "leg": "legend",
    "sect": "section",
    "art": "article",
    "hdr": "header",
    "ftr": "footer",
    "adr": "address",
    "dlg": "dialog",
    "str": "strong",
    "prog": "progress",
    "mn": "main",
    "tem": "template",
    "datag": "datagrid",
    "datal": "datalist",
    "out": "output",
    "det": "details",
    "sum": "summary",
    # expandos: "name+" expands to the element with its usual child
    "ul+": "ul>li",
    "ol+": "ol>li",
    "dl+": "dl>dt+dd",
    "map+": "map>area",
    "table+": "table>tr>td",
    "colgroup+|colg+": "colgroup>col",
    "tr+": "tr>td",
    "select+": "select>option",
    "optgroup+|optg+": "optgroup>option",
}

_RAW_XSL_SNIPPETS = {
    "tm|tmatch": "xsl:template[match mode]",
    "tn|tname": "xsl:template[name]",
    "call": "xsl:call-template[name]",
    "ap": "xsl:apply-templates[select mode]",
    "api": "xsl:apply-imports",
    "imp": "xsl:import[href]",
    "inc": "xsl:include[href]",
    "ch|xsl:when": "xsl:choose",
    "wh": "xsl:when[test]",
    "ot": "xsl:otherwise",
    "if": "xsl:if[test]",
    "par": "xsl:param[name]",
    "pare": "xsl:param[name select]",
    "var": "xsl:variable[name]",
    "vare": "xsl:variable[name select]",
    "wp": "xsl:with-param[name select]",
    "key": "xsl:key[name match use]",
    "elem": "xsl:element[name]",
    "attr": "xsl:attribute[name]",
    "attrs": "xsl:attribute-set[name]",
    "cp": "xsl:copy[select]",
    "co": "xsl:copy-of[select]",
    "val": "xsl:value-of[select]",
    "each|for": "xsl:for-each[select]",
    "tex": "xsl:text",
    "cmt": "xsl:comment",
    "msg": "xsl:message[terminate=no]",
    "fall": "xsl:fallback",
    "num": "xsl:number[value]",
    "nam": "xsl:namespace-alias[stylesheet-prefix result-prefix]",
    "pres": "xsl:preserve-space[elements]",
    "strip": "xsl:strip-space[elements]",
    "proc": "xsl:processing-instruction[name]",
    "sort": "xsl:sort[select order]",
    "choose+": "xsl:choose>xsl:when+xsl:otherwise",
    "xsl": "xsl:stylesheet[version=1.0 xmlns:xsl=http://www.w3.org/1999/XSL/Transform]",
}


def _flatten(raw: dict) -> dict:
    out = {}
    for keys, value in raw.items():
        for key in keys.split("|"):
            out[key] = value
    return out


HTML_SNIPPETS = _flatten(_RAW_SNIPPETS)
XSL_SNIPPETS = _flatten(_RAW_XSL_SNIPPETS)

LOREM_WORDS = (
    "lorem ipsum dolor sit amet consectetur adipisicing elit sed do eiusmod tempor incididunt "
    "ut labore et dolore magna aliqua enim ad minim veniam quis nostrud exercitation ullamco "
    "laboris nisi aliquip ex ea commodo consequat duis aute irure in reprehenderit voluptate "
    "velit esse cillum eu fugiat nulla pariatur excepteur sint occaecat cupidatat non proident "
    "sunt culpa qui officia deserunt mollit anim id est laborum perspiciatis unde omnis iste "
    "natus error voluptatem accusantium doloremque laudantium totam rem aperiam eaque ipsa quae "
    "ab illo inventore veritatis quasi architecto beatae vitae dicta explicabo nemo ipsam quia "
    "voluptas aspernatur aut odit fugit consequuntur magni dolores eos ratione sequi nesciunt "
    "neque porro quisquam dolorem adipisci numquam eius modi tempora incidunt magnam quaerat"
).split()
