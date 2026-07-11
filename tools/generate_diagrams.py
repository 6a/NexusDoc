#!/usr/bin/env python3
"""
NexusDoc ASCII diagram generator.
Run:  python tools/generate_diagrams.py [output-file]

Layout rules (all derived from OUTER_W):

    OUTER_W = 65     total diagram width including ││ side borders
    INNER_W = 63     content width between ││  (= OUTER_W - 2)
    PAD     =  2     standard left/right padding within ││
    CONT_W  = 59     usable content width (= INNER_W - 2*PAD = OUTER_W - 6)

    3-box row (lpad=2, rpad=2, gap=1):
        sub_w = (INNER_W - lpad - rpad - 2*gap) / 3 - 2  = 17
        lpad + 3*(sub_w+2) + 2*gap + rpad  =  63  =  INNER_W  ✓

    Arrow column positions (within INNER_W):
        col_i = lpad + i*(sub_w + 2 + gap) + 1 + sub_w//2

    Inner-box dimensions:
        Border line = ┌ + SIW + ┐  where SIW = inner content width
        Wrapped as:  PAD_spaces + border_line + PAD_spaces
        Must total ≤ INNER_W.  With SIW = 57: 2 + 59 + 2 = 63 = INNER_W ✓
"""

import sys

# ═══════════════════════════════════════════════════════════════════
# Layout constants  (only OUTER_W is a free parameter)
# ═══════════════════════════════════════════════════════════════════

OUTER_W = 65
INNER_W = OUTER_W - 2                                          # 63
PAD = 2                                                         # 2
CONT_W = INNER_W - 2 * PAD                                       # 59

# 3-box row defaults
LPAD, RPAD, GAP = 2, 2, 1
SUB_W = (INNER_W - LPAD - RPAD - 2 * GAP) // 3 - 2              # 17

# Inner-box content width (border = SIW + 2 → padded → INNER_W)
SIW = CONT_W - 2                                                # 57

# Single-arrow centre column
CP = INNER_W // 2                                                # 31

# Derived box parameters for Vector Store's 3 sub-boxes
VS_SUB_W = 15
VS_LPAD = 2
VS_RPAD = 0
VS_GAP = 2
# verification: VS_LPAD + 3*(VS_SUB_W+2) + 2*VS_GAP + VS_RPAD = 2+51+4+0 = 57 = SIW ✓

# ─── assertions ──────────────────────────────────────────────────
assert OUTER_W == 65
assert INNER_W == 63
assert PAD == 2
assert CONT_W == 59
assert SUB_W == 17
assert SIW == 57
assert CP == 31


# ═══════════════════════════════════════════════════════════════════
# Primitives
# ═══════════════════════════════════════════════════════════════════

def hline(w=INNER_W):
    return '┌' + '─' * w + '┐'

def rline(w=INNER_W):
    return '└' + '─' * w + '┘'

def center(text, w=INNER_W):
    t = str(text)
    if len(t) >= w:
        return t[:w]
    l = (w - len(t)) // 2
    r = w - len(t) - l
    return ' ' * l + t + ' ' * r

def left(text, w=INNER_W):
    t = str(text)[:w]
    return t + ' ' * (w - len(t))

def wrap(line, w=INNER_W):
    """Pad `line` to `w` chars, then wrap in ││."""
    # The caller guarantees line fits, but truncate as a safety net.
    if len(line) > w:
        line = line[:w]
    return '│' + line.ljust(w) + '│'

def spacer():
    return wrap(' ' * INNER_W)


# ═══════════════════════════════════════════════════════════════════
# 3-box row builder
# ═══════════════════════════════════════════════════════════════════

def three_box_row(texts, sub_w=SUB_W, lpad=LPAD, rpad=RPAD, gap=GAP, no_ports=False):
    """
    Return (top, mid, bot) – three INNER_W-char content strings.
    Each string is meant to be passed through wrap().
    When `no_ports=True`, the bottom line uses plain └──┘ (no ┬ connectors).
    """
    assert len(texts) == 3

    def _top():
        s = ' ' * lpad
        for i in range(3):
            s += '┌' + '─' * sub_w + '┐'
            s += ' ' * gap if i < 2 else ''
        return s + ' ' * rpad

    def _mid():
        s = ' ' * lpad
        for i, txt in enumerate(texts):
            t = center(txt, sub_w)
            s += '│' + t + '│'
            s += ' ' * gap if i < 2 else ''
        return s + ' ' * rpad

    def _bot():
        s = ' ' * lpad
        for i in range(3):
            if no_ports:
                s += '└' + '─' * sub_w + '┘'
            else:
                ld = sub_w // 2
                rd = sub_w - ld - 1
                s += '└' + '─' * ld + '┬' + '─' * rd + '┘'
            s += ' ' * gap if i < 2 else ''
        return s + ' ' * rpad

    return _top(), _mid(), _bot()


def tb_positions(sub_w=SUB_W, lpad=LPAD, gap=GAP):
    """3 ┬ column positions in the INNER_W-char field."""
    total = sub_w + 2
    mid = sub_w // 2
    return [lpad + i * (total + gap) + 1 + mid for i in range(3)]


# ═══════════════════════════════════════════════════════════════════
# Arrow / filler helpers
# ═══════════════════════════════════════════════════════════════════

def filler_line(char, pos, w=INNER_W):
    """w-char string with `char` at each column in `pos`, spaces elsewhere."""
    chars = [' '] * w
    for p in pos:
        chars[p] = char
    return ''.join(chars)


def three_arrows(pos):
    """Return two wrapped lines – stems, then arrowheads – at positions `pos`."""
    return [wrap(filler_line('│', pos)), wrap(filler_line('▼', pos))]


def single_arrow():
    return [wrap(' ' * CP + '│' + ' ' * CP), wrap(' ' * CP + '▼' + ' ' * CP)]


def section_label(text):
    """Append spacer, centred label, spacer to `out`."""
    return [spacer(), wrap(center(text)), spacer()]


# ═══════════════════════════════════════════════════════════════════
# Inner-box builder  (observability / guardrails)
# ═══════════════════════════════════════════════════════════════════

def inner_box(title, bullets):
    """
    Produce wrapped lines for a box with inner width SIW (= 57).
    The box border is SIW+2 wide; padded with PAD spaces on each side
    the total becomes INNER_W before wrap().  We pass the raw string
    (which is SIW+2 + 2*PAD = 63 = INNER_W) directly to wrap().
    """
    # Raw box border: ┌ + SIW + ┐  (SIW+2 chars)
    raw_top = '┌' + '─' * SIW + '┐'
    raw_bot = '└' + '─' * SIW + '┘'
    # Content: SIW-wide title + bullet lines
    lines = [raw_top,
             center(title, SIW + 2)] + \
            [left('  ' + b, SIW) for b in bullets] + \
            [raw_bot]
    # Each line padded by PAD on left+right → total INNER_W → wrap
    return [wrap(' ' * PAD + l + ' ' * PAD) for l in lines]


# ═══════════════════════════════════════════════════════════════════
# Supervisor Agent internal lines
# ═══════════════════════════════════════════════════════════════════

def supervisor_lines():
    """
    Return SIW-wide strings for the supervisor inner box.

    Logical flow (from README detail):
        classify_document_type  →  route_to_agents  (single dispatch)
            │                                          │
            ▼                                          ▼
        4 parallel agents  ─── collect_results  ───  validate  ─→  format_output

    Agent boxes are 10-char interior, 12-char with borders.
    Four boxes at indent 4, gap 1.
    ┬ positions: box-1=10, box-2=23, box-3=36, box-4=49.
    Merge 1→2 at midpoint 16; merge 3→4 at midpoint 42.
    Cross-merge at midpoint 29 → collect_results.
    """
    S = SIW  # 57

    def cl(text, indent=0):
        """Left-align text with indent, padding to S."""
        return left(' ' * indent + text, S)

    def st(*cols):
        """Stem line with │ at given column(s)."""
        chars = [' '] * S
        for c in cols:
            if 0 <= c < S:
                chars[c] = '│'
        return ''.join(chars)

    def ar(*cols):
        """Arrow line with ▼ at given column(s)."""
        chars = [' '] * S
        for c in cols:
            if 0 <= c < S:
                chars[c] = '▼'
        return ''.join(chars)

    C = S // 2  # centre column = 28

    return [
        '┌' + '─' * SIW + '┐',
        center('Supervisor Agent (StateGraph)', S),
        center('Routes by document type + user query intent', S),
        left('', S),
        # ── classify / route ──
        center('classify_document_type', S),
        st(C),
        ar(C),
        center('route_to_agents', S),
        st(C),
        ar(C),
        left('', S),
        # ── 4 agent boxes ──
        left('    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐', S),
        left('    │   DQA    │ │  Table   │ │   Risk   │ │Summarizer│', S),
        left('    │  Agent   │ │ QA Agent │ │Classifier│ │  Agent   │', S),
        left('    └─────┬────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘', S),
        # ── 4 stems from box ┬ positions (10, 23, 36, 49) ──
        st(10, 23, 36, 49),
        ar(10, 23, 36, 49),
        # ── merge 1→2 (col 10→23) and 3→4 (col 36→49) ──
        # Each bridge: └ + 5─ + ┬ + 6─ + ┘ = 14 chars, ┬ at index 6
        left('          └─────┬──────┘            └─────┬──────┘', S),
        st(16, 42),
        ar(16, 42),
        # ── cross-merge into single stem (cols 16+42 → 29) ──
        # Bridge: └ + 12─ + ┬ + 12─ + ┘ = 27 chars, ┬ at index 13
        # At indent 16 → ┬ at SIW 16+13=29 → inner 2+29=31 = CP ✓
        left('                └────────────┬────────────┘', S),
        st(29),
        ar(29),
        # ── collect / validate ──
        center('collect_results', S),
        st(29),
        ar(29),
        center('validate -> format_output', S),
        '└' + '─' * SIW + '┘',
    ]


# ═══════════════════════════════════════════════════════════════════
# BUILD: High-Level System Flow
# ═══════════════════════════════════════════════════════════════════

def build_flow():
    """
    Entire flow sits inside ONE outer box (┌─┐ … └─┘).
    Every content line passes through wrap() so ││ side-borders are
    consistent.  Section labels float as centred text; transitions use
    clean arrows with no orphaned connector lines.
    """
    out = []

    # ───── outer box top ─────
    out.append(hline(INNER_W))

    # ── 1. User Input Layer ──
    out.append(wrap(center('User Input Layer')))
    t, m, b = three_box_row(
        [center('Upload PDF', SUB_W), center('SEC Ticker', SUB_W), center('URL / Microphone', SUB_W)]
    )
    out.append(wrap(t))
    out.append(wrap(m))
    out.append(wrap(b))
    pos = tb_positions()
    out.extend(three_arrows(pos))

    # ── 2. Ingestion Pipeline ──
    out.extend(section_label('Ingestion Pipeline (Prefect)'))
    t, m, b = three_box_row(
        [center('PDF Extraction', SUB_W), center('Layout Analysis', SUB_W), center('Text Chunking', SUB_W)]
    )
    out.append(wrap(t))
    out.append(wrap(m))
    out.append(wrap(b))
    out.extend(three_arrows(pos))

    # ── 2b. Vector Store box (nested inside Ingestion) ──
    t2, m2, b2 = three_box_row(
        [center('Text Chunks', VS_SUB_W), center('Table Cells', VS_SUB_W), center('Image Layouts', VS_SUB_W)],
        sub_w=VS_SUB_W, lpad=VS_LPAD, rpad=VS_RPAD, gap=VS_GAP
    )
    vs_lines = [
        '┌' + '─' * SIW + '┐',
        center('Vector Store (pgvector)', SIW + 2),
        t2, m2, b2,
        '└' + '─' * SIW + '┘',
    ]
    for l in vs_lines:
        out.append(wrap(' ' * PAD + l + ' ' * PAD))

    out.extend(single_arrow())

    # ── 3. LangGraph Orchestrator ──
    out.extend(section_label('LangGraph Multi-Agent Orchestrator'))
    for s in supervisor_lines():
        out.append(wrap(' ' * PAD + s + ' ' * PAD))

    out.extend(single_arrow())

    # ── 4. Output Layer + Observability ──
    out.extend(section_label('Output Layer + Observability'))
    t, m, b = three_box_row(
        [center('Structured JSON', SUB_W), center('Chat UI', SUB_W), center('Audio Briefing', SUB_W)],
        no_ports=True
    )
    out.append(wrap(t))
    out.append(wrap(m))
    out.append(wrap(b))
    out.append(spacer())

    obs = inner_box('Observability (LangFuse self-hosted)', [
        '* Span-level traces for every agent step',
        '* Token & cost tracking per document',
        '* LLM-as-judge evaluation scores',
    ])
    out.extend(obs)
    out.append(spacer())

    grd = inner_box('Guardrails (NeMo Guardrails)', [
        '* PII masking in documents and queries',
        '* Topic enforcement (reject off-topic questions)',
        '* Toxicity filter on outputs',
    ])
    out.extend(grd)

    # ───── outer box bottom ─────
    out.append(rline(INNER_W))
    return out


# ═══════════════════════════════════════════════════════════════════
# Model Registry (separate box)
# ═══════════════════════════════════════════════════════════════════

def build_registry():
    out = [hline(INNER_W),
           wrap(center('Model Registry (configurable)')),
           spacer(),
           wrap(left('  DEFAULT_PROVIDER=groq           # Primary runtime')),
           wrap(left('  FALLBACK_PROVIDER=openrouter    # Rate-limit fallback')),
           wrap(left('  OFFLINE_PROVIDER=ollama         # Local development')),
           wrap(left('  EVAL_PROVIDER=openrouter        # Evaluation (different)')),
           spacer(),
           wrap(left('  Embedding: sentence-transformers (local, always free)')),
           rline(INNER_W)]
    return out


# ═══════════════════════════════════════════════════════════════════
# Verification
# ═══════════════════════════════════════════════════════════════════

def verify(lines, name):
    ok = True
    for i, l in enumerate(lines):
        if len(l) != OUTER_W:
            print(f"  [{i}] len={len(l)} expected {OUTER_W}", file=sys.stderr)
            ok = False
    if ok:
        print(f"  {name}: {len(lines)} lines, all {OUTER_W} chars.", file=sys.stderr)
    return ok


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    flow = build_flow()
    reg = build_registry()

    all_ok = True
    if not verify(flow, 'High-Level Flow'):
        all_ok = False
    if not verify(reg, 'Model Registry'):
        all_ok = False

    if not all_ok:
        print("ERROR: Verification failed!", file=sys.stderr)
        sys.exit(1)

    out_name = sys.argv[1] if len(sys.argv) > 1 else '-'
    fout = open(out_name, 'w', encoding='utf-8') if out_name != '-' else sys.stdout

    fout.write("### High-Level System Flow\n\n")
    fout.write("```\n")
    for l in flow:
        fout.write(l + '\n')
    fout.write("```\n\n")
    fout.write("```\n")
    for l in reg:
        fout.write(l + '\n')
    fout.write("```\n\n")

    if out_name != '-':
        fout.close()


if __name__ == '__main__':
    main()
