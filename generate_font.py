import random
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


UPM = 1000
ASCENT = 800
DESCENT = -200
ADVANCE = 600

NUM_STATES = 16
NUM_CLASSES = 7


PRINTABLE = (
    list(range(0x20, 0x7F))
    + list(range(0xA0, 0x100))
    + [
        0x2013, 0x2014,
        0x2018, 0x2019,
        0x201C, 0x201D,
        0x2022,
        0x2026,
        0x20AC,
        0x2122,
        0x2190, 0x2191, 0x2192, 0x2193,
    ]
)


random.seed(42)


all_states = list(range(NUM_STATES))
random.shuffle(all_states)
SLASH_STATES = set(all_states[:NUM_STATES // 2])
BACKSLASH_STATES = set(all_states[NUM_STATES // 2:])


INITIAL_STATE = {cp: random.randint(0, NUM_STATES - 1) for cp in PRINTABLE}


def make_derangement(n):


    while True:
        perm = list(range(n))
        random.shuffle(perm)
        if all(perm[i] != i for i in range(n)):
            return perm


TRANSITIONS = {}
for c in range(NUM_CLASSES):
    TRANSITIONS[c] = make_derangement(NUM_STATES)


print(f"Slash states:     {sorted(SLASH_STATES)}")
print(f"Backslash states: {sorted(BACKSLASH_STATES)}")
for c in range(NUM_CLASSES):
    shapes = ''.join('/' if TRANSITIONS[c][s] in SLASH_STATES else 'b' for s in range(NUM_STATES))
    print(f"  Class {c} transitions: {TRANSITIONS[c]}  -> shapes: {shapes}")


def glyph_name(codepoint, state=0):


    if codepoint == 0x20:
        base = "space"
    else:
        base = f"uni{codepoint:04X}"
    return base if state == 0 else f"{base}.s{state}"


def draw_slash():


    pen = TTGlyphPen(None)
    pen.moveTo((100, -150))
    pen.lineTo((180, -150))
    pen.lineTo((480, 750))
    pen.lineTo((400, 750))
    pen.closePath()
    return pen.glyph()


def draw_backslash():


    pen = TTGlyphPen(None)
    pen.moveTo((100, 750))
    pen.lineTo((180, 750))
    pen.lineTo((480, -150))
    pen.lineTo((400, -150))
    pen.closePath()
    return pen.glyph()


def draw_empty():

    pen = TTGlyphPen(None)
    return pen.glyph(dropImpliedOnCurves=False)


SLASH_GLYPH = draw_slash()
BACKSLASH_GLYPH = draw_backslash()
EMPTY_GLYPH = draw_empty()


glyphs = {".notdef": EMPTY_GLYPH}

for cp in PRINTABLE:
    for state in range(NUM_STATES):
        name = glyph_name(cp, state)
        if cp == 0x20:

            glyphs[name] = EMPTY_GLYPH
        elif state in SLASH_STATES:
            glyphs[name] = SLASH_GLYPH
        else:
            glyphs[name] = BACKSLASH_GLYPH


glyph_order = [".notdef"]
for cp in PRINTABLE:
    for state in range(NUM_STATES):
        glyph_order.append(glyph_name(cp, state))


def build_feature_code():


    lines = []


    for s in range(NUM_STATES):
        members = " ".join(glyph_name(cp, s) for cp in PRINTABLE)
        lines.append(f"@s{s} = [{members}];")


    all_members = " ".join(
        glyph_name(cp, s) for cp in PRINTABLE for s in range(NUM_STATES)
    )
    lines.append(f"@allchars = [{all_members}];")
    lines.append("")


    for class_id in range(NUM_CLASSES):
        class_cps = [cp for cp in PRINTABLE if cp % NUM_CLASSES == class_id]
        for s in range(NUM_STATES):
            members = " ".join(glyph_name(cp, s) for cp in class_cps)
            lines.append(f"@cc{class_id}_s{s} = [{members}];")
    lines.append("")


    for target_s in range(NUM_STATES):
        lines.append(f"lookup to_s{target_s} {{")
        for source_s in range(NUM_STATES):
            if source_s == target_s:
                continue
            from_class = " ".join(glyph_name(cp, source_s) for cp in PRINTABLE)
            to_class = " ".join(glyph_name(cp, target_s) for cp in PRINTABLE)
            lines.append(f"  sub [{from_class}] by [{to_class}];")
        lines.append(f"}} to_s{target_s};")
        lines.append("")


    lines.append("feature calt {")
    lines.append("  lookup chain {")
    for class_id in range(NUM_CLASSES):
        for current_s in range(NUM_STATES):
            target_s = TRANSITIONS[class_id][current_s]
            lines.append(
                f"    sub @cc{class_id}_s{current_s} @allchars' lookup to_s{target_s};"
            )
    lines.append("  } chain;")
    lines.append("} calt;")

    return "\n".join(lines)


fb = FontBuilder(UPM, isTTF=True)


fb.setupGlyphOrder(glyph_order)


fb.setupCharacterMap({cp: glyph_name(cp, INITIAL_STATE[cp]) for cp in PRINTABLE})


fb.setupGlyf(glyphs)


metrics = {}
for name in glyph_order:
    if glyphs[name] is EMPTY_GLYPH:
        metrics[name] = (ADVANCE, 0)
    else:
        metrics[name] = (ADVANCE, 100)
fb.setupHorizontalMetrics(metrics)


fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT)
fb.setupNameTable({
    "familyName": "SlashMatrix",
    "styleName": "Regular",
})
fb.setupOS2(
    sTypoAscender=ASCENT,
    sTypoDescender=DESCENT,
    usWinAscent=ASCENT,
    usWinDescent=abs(DESCENT),
)
fb.setupPost()


print("Generating OpenType feature code...")
fea_code = build_feature_code()
fb.addOpenTypeFeatures(fea_code)


output = "slash_matrix.ttf"
fb.font.save(output)
print(f"Done! Font saved to {output}")
print(f"  Glyphs: {len(glyph_order)}")
print(f"  States: {NUM_STATES} ({len(SLASH_STATES)} slash, {len(BACKSLASH_STATES)} backslash)")
print(f"  Classes: {NUM_CLASSES} (codepoint % {NUM_CLASSES})")
print(f"  Chain rules: {NUM_CLASSES * NUM_STATES}")
