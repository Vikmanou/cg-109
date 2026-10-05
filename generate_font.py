import random
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

ADVANCE, ASCENT, DESCENT = 600, 800, -200
STATES, GROUPS = 16, 7
CHARS = [*range(0x20, 0x7F), *range(0xA0, 0x100), 0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x20AC, 0x2122, 0x2190, 0x2191, 0x2192, 0x2193]
SPACES = {0x20, 0xA0}

random.seed(42)
order = list(range(STATES))
random.shuffle(order)
SLASH = set(order[:STATES // 2])
INITIAL = {cp: random.randint(0, STATES - 1) for cp in CHARS}


def cycle(n):


    order = list(range(n))
    random.shuffle(order)
    p = [0] * n
    for i in range(n):
        p[order[i]] = order[(i + 1) % n]
    return p


NEXT = [cycle(STATES) for _ in range(GROUPS)]


def family(cp):
    return (cp % GROUPS, cp in SPACES)


FAMILIES = sorted({family(cp) for cp in CHARS})


def name(fam, s):
    g, blank = fam
    return f"g{g}{'b' if blank else ''}.s{s}"


def poly(*pts):
    pen = TTGlyphPen(None)
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()
    return pen.glyph()


def features():
    cls = lambda label, fams, s: f"@{label} = [{' '.join(name(f, s) for f in fams)}];"
    out = [cls(f"s{s}", FAMILIES, s) for s in range(STATES)]
    for g in range(GROUPS):
        out += [cls(f"g{g}s{s}", [f for f in FAMILIES if f[0] == g], s) for s in range(STATES)]
    out.append(f"@any = [{' '.join(f'@s{s}' for s in range(STATES))}];")

    for t in range(STATES):
        out += [f"lookup set{t} {{", *(f"sub @s{s} by @s{t};" for s in range(STATES) if s != t), f"}} set{t};"]

    out.append("feature calt {")
    out += [f"sub @g{g}s{s} @any' lookup set{NEXT[g][s]};" for g in range(GROUPS) for s in range(STATES)]
    out.append("} calt;")
    return "\n".join(out)


empty = TTGlyphPen(None).glyph()
shape = {
    True: poly((100, -150), (400, 750), (480, 750), (180, -150)),
    False: poly((100, 750), (180, 750), (480, -150), (400, -150)),
}
glyphs = {".notdef": empty}
for fam in FAMILIES:
    for s in range(STATES):
        glyphs[name(fam, s)] = empty if fam[1] else shape[s in SLASH]

fb = FontBuilder(1000, isTTF=True)
fb.updateHead(created=2082844800, modified=2082844800)
fb.setupGlyphOrder(list(glyphs))
fb.setupCharacterMap({cp: name(family(cp), INITIAL[cp]) for cp in CHARS})
fb.setupGlyf(glyphs)
fb.setupHorizontalMetrics({n: (ADVANCE, getattr(g, "xMin", 0)) for n, g in glyphs.items()})
fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT)
fb.setupNameTable({"familyName": "Slashes", "styleName": "Regular"}, mac=False)
fb.setupOS2(sTypoAscender=ASCENT, sTypoDescender=DESCENT, usWinAscent=ASCENT, usWinDescent=-DESCENT)
fb.setupPost(keepGlyphNames=False)
fb.addOpenTypeFeatures(features())
fb.save("slash.ttf")
