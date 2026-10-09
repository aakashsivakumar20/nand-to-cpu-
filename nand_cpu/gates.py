"""
gates.py — Layer 1: Combinational Logic

Every gate here is built from a single primitive: Nand().
GATE_COUNT tracks how many NAND gates have fired, so we can report
the "circuit cost" of any computation later (used by the CPU's
gate-cost visualizer).
"""

GATE_COUNT = 0


def reset_gate_count():
    global GATE_COUNT
    GATE_COUNT = 0


def count_physical(n):
    """Manually attribute n physical NAND gates to the global counter.

    GATE-COUNTING RULE FOR FEEDBACK CIRCUITS (latches/flip-flops,
    registers.py): a cross-coupled NAND pair has no single-pass order —
    computing its settled output means re-evaluating the same two gates
    in software until the values stop changing. That iteration is a
    software artifact of simulating feedback with no propagation delay;
    in real hardware it is still just N physical gates, each firing once
    per clock phase, not once per settle iteration. So feedback circuits
    must NOT call the counted Nand() during their internal settle loop
    (use the uncounted raw NAND below instead) — they call this function
    exactly once per invocation, with n = the number of physical gates in
    that circuit, however many iterations settling took.
    """
    global GATE_COUNT
    GATE_COUNT += n


def nand_raw(a, b):
    """Uncounted NAND — for internal use only, inside the settle loop of a
    feedback circuit (see count_physical above). Never call this from
    ordinary combinational code; use Nand() so the gate counter stays
    accurate."""
    return 0 if (a and b) else 1


def Nand(a, b):
    """The one and only primitive gate. Everything else is built from this."""
    global GATE_COUNT
    GATE_COUNT += 1
    return 0 if (a and b) else 1


def Not(a):
    return Nand(a, a)


def And(a, b):
    return Not(Nand(a, b))


def Or(a, b):
    return Nand(Not(a), Not(b))


def Xor(a, b):
    return And(Or(a, b), Nand(a, b))


def Mux(a, b, sel):
    """sel = 0 -> a, sel = 1 -> b"""
    return Or(And(a, Not(sel)), And(b, sel))


def DMux(inp, sel):
    """sel = 0 -> (in, 0), sel = 1 -> (0, in)"""
    return And(inp, Not(sel)), And(inp, sel)


# ---- 16-bit (bus) versions — bit-lists, index 0 = LSB ----

def Not16(a):
    return [Not(x) for x in a]


def And16(a, b):
    return [And(x, y) for x, y in zip(a, b)]


def Or16(a, b):
    return [Or(x, y) for x, y in zip(a, b)]


def Mux16(a, b, sel):
    return [Mux(x, y, sel) for x, y in zip(a, b)]


def Or16Way(a):
    """OR every bit of a 16-bit bus together -> 1 if ANY bit is 1."""
    result = 0
    for bit in a:
        result = Or(result, bit)
    return result
