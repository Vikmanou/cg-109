# slash.ttf builder

import random

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

UNITS_PER_EM = 1000
ADVANCE = 600
ASCENT = 800
DESCENT = -200

SEED = 42
STATES = 16
GROUPS = 7

CHARS = [
    *range(0x20, 0x7F),
    *range(0xA0, 0x100),
] + [ord(character) for character in "–—‘’“”•…€™←↑→↓"]
SPACES = {0x20, 0xA0}


def family(codepoint):
    return (codepoint % GROUPS, codepoint in SPACES)


FAMILIES = sorted({family(codepoint) for codepoint in CHARS})


def single_cycle(state_count, rng):
    order = list(range(state_count))
    rng.shuffle(order)

    next_states = [0] * state_count
    for index, state in enumerate(order):
        next_states[state] = order[(index + 1) % state_count]
    return next_states


def build_state_machine():
    rng = random.Random(SEED)

    order = list(range(STATES))
    rng.shuffle(order)
    slash_states = set(order[:STATES // 2])

    initial_states = {}
    for codepoint in CHARS:
        initial_states[codepoint] = rng.randint(0, STATES - 1)

    next_states = []
    for group in range(GROUPS):
        next_states.append(single_cycle(STATES, rng))

    return slash_states, initial_states, next_states


def glyph_name(glyph_family, state):
    group, is_blank = glyph_family
    blank_marker = "b" if is_blank else ""
    return f"g{group}{blank_marker}.s{state}"


def draw_polygon(points):
    pen = TTGlyphPen(None)
    pen.moveTo(points[0])
    for point in points[1:]:
        pen.lineTo(point)
    pen.closePath()
    return pen.glyph()


def build_glyphs(slash_states):
    empty = TTGlyphPen(None).glyph()
    slash = draw_polygon([(100, -150), (400, 750), (480, 750), (180, -150)])
    backslash = draw_polygon([(100, 750), (180, 750), (480, -150), (400, -150)])

    glyphs = {".notdef": empty}
    for glyph_family in FAMILIES:
        _, is_blank = glyph_family
        for state in range(STATES):
            if is_blank:
                outline = empty
            elif state in slash_states:
                outline = slash
            else:
                outline = backslash
            glyphs[glyph_name(glyph_family, state)] = outline
    return glyphs


def glyph_class(label, families, state):
    names = [glyph_name(glyph_family, state) for glyph_family in families]
    return f"@{label} = [{' '.join(names)}];"


def build_features(next_states):
    lines = []

    # Matching family order makes substitutions preserve the glyph family.
    for state in range(STATES):
        lines.append(glyph_class(f"s{state}", FAMILIES, state))

    for group in range(GROUPS):
        group_families = [glyph_family for glyph_family in FAMILIES if glyph_family[0] == group]
        for state in range(STATES):
            lines.append(glyph_class(f"g{group}s{state}", group_families, state))

    state_classes = [f"@s{state}" for state in range(STATES)]
    lines.append(f"@any = [{' '.join(state_classes)}];")

    for target_state in range(STATES):
        lines.append(f"lookup set{target_state} {{")
        for source_state in range(STATES):
            if source_state != target_state:
                lines.append(f"sub @s{source_state} by @s{target_state};")
        lines.append(f"}} set{target_state};")

    # The previous glyph already has its state; the apostrophe marks the current one.
    lines.append("feature calt {")
    for group in range(GROUPS):
        for state in range(STATES):
            target_state = next_states[group][state]
            lines.append(f"sub @g{group}s{state} @any' lookup set{target_state};")
    lines.append("} calt;")

    return "\n".join(lines)


def build_font(output_path="slash.ttf"):
    slash_states, initial_states, next_states = build_state_machine()
    glyphs = build_glyphs(slash_states)

    character_map = {}
    for codepoint in CHARS:
        character_map[codepoint] = glyph_name(family(codepoint), initial_states[codepoint])

    font = FontBuilder(UNITS_PER_EM, isTTF=True)

    # Fixed timestamps keep builds reproducible.
    font.updateHead(created=2082844800, modified=2082844800)
    font.setupGlyphOrder(list(glyphs))
    font.setupCharacterMap(character_map)
    font.setupGlyf(glyphs)

    metrics = {}
    for name, glyph in glyphs.items():
        left_side_bearing = glyph.xMin if glyph.numberOfContours else 0
        metrics[name] = (ADVANCE, left_side_bearing)
    font.setupHorizontalMetrics(metrics)

    font.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT)
    font.setupNameTable({"familyName": "Slashes", "styleName": "Regular"}, mac=False)
    font.setupOS2(
        sTypoAscender=ASCENT,
        sTypoDescender=DESCENT,
        usWinAscent=ASCENT,
        usWinDescent=-DESCENT,
    )

    font.setupPost(keepGlyphNames=False)
    font.addOpenTypeFeatures(build_features(next_states))
    font.save(output_path)


if __name__ == "__main__":
    build_font()
