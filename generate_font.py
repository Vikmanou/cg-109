import random
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

ADVANCE, ASCENT, DESCENT = 600, 800, -200
STATES, GROUPS = 16, 7
CHARS = [*range(0x20, 0x7F), *range(0xA0, 0x100), 0x2013, 0x2014, 0x2018, 0x2019, 0x201C,
         0x201D, 0x2022, 0x2026, 0x20AC, 0x2122, 0x2190, 0x2191, 0x2192, 0x2193]
SPACES = {0x20, 0xA0}


random.seed(42)
order = list(range(STATES))
random.shuffle(order)
SLASH = set(order[:STATES // 2])
INITIAL = {cp: random.randint(0, STATES - 1) for cp in CHARS}


def derangement(n):
    while True:
        p = list(range(n))
        random.shuffle(p)
        if all(p[i] != i for i in range(n)):
            return p


NEXT = [derangement(STATES) for _ in range(GROUPS)]


def name(cp, s):
    return f"u{cp:04X}.s{s}"


def poly(*pts):
    pen = TTGlyphPen(None)
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()
    return pen.glyph()


def ref(base, glyphs):
    pen = TTGlyphPen(glyphs)
    pen.addComponent(base, (1, 0, 0, 1, 0, 0))
    return pen.glyph()


def features():
    cls = lambda label, cps, s: f"@{label} = [{' '.join(name(cp, s) for cp in cps)}];"
    out = [cls(f"s{s}", CHARS, s) for s in range(STATES)]
    for g in range(GROUPS):
        out += [cls(f"g{g}s{s}", [cp for cp in CHARS if cp % GROUPS == g], s) for s in range(STATES)]
    out.append(f"@any = [{' '.join(f'@s{s}' for s in range(STATES))}];")

    for t in range(STATES):
        out += [f"lookup set{t} {{", *(f"sub @s{s} by @s{t};" for s in range(STATES) if s != t), f"}} set{t};"]

    out.append("feature calt {")
    out += [f"sub @g{g}s{s} @any' lookup set{NEXT[g][s]};" for g in range(GROUPS) for s in range(STATES)]
    out.append("} calt;")
    return "\n".join(out)


base = {
    "_slash": poly((100, -150), (400, 750), (480, 750), (180, -150)),
    "_backslash": poly((100, 750), (180, 750), (480, -150), (400, -150)),
}
empty = TTGlyphPen(None).glyph()
shape = {True: ref("_slash", base), False: ref("_backslash", base)}
glyphs = {".notdef": empty}
for cp in CHARS:
    for s in range(STATES):
        glyphs[name(cp, s)] = empty if cp in SPACES else shape[s in SLASH]
glyphs |= base

fb = FontBuilder(1000, isTTF=True)
fb.setupGlyphOrder(list(glyphs))
fb.setupCharacterMap({cp: name(cp, INITIAL[cp]) for cp in CHARS})
fb.setupGlyf(glyphs)
glyf = fb.font["glyf"]
fb.setupHorizontalMetrics({n: (ADVANCE, getattr(glyf[n], "xMin", 0)) for n in glyphs})
fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT)
fb.setupNameTable({"familyName": "Slashes", "styleName": "Regular"}, mac=False)
fb.setupOS2(sTypoAscender=ASCENT, sTypoDescender=DESCENT, usWinAscent=ASCENT, usWinDescent=-DESCENT)
fb.setupPost()
fb.addOpenTypeFeatures(features())
fb.save("slash.ttf")
