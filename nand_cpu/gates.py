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
