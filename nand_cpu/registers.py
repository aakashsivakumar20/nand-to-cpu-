"""
registers.py — Layer 3b: memory built from NAND gates, not modelled by hand.

memory.py's Register/RAM are a *behavioural* model: `self.bits = list(...)`
on load, i.e. Python's own assignment stands in for "a register remembers a
value". This module instead builds that memory the way real hardware does,
bottom-up, from nothing but Nand():

    cross-coupled NAND pair (SR latch)
      -> gated D latch (adds an enable so S/R can never both be asserted)
        -> master-slave D flip-flop (adds a second latch so it only
           captures on the clock edge, not for the whole time D is high)
          -> Bit (1-bit cell with a load input)
            -> GateRegister (16 Bits sharing one load line)
              -> RAM8 (8 GateRegisters behind a 3-bit address decoder)

GATE COUNTING: see gates.count_physical's docstring. In short — a
feedback loop (the SR latch's cross-coupled pair) is iteratively
re-evaluated in software to find where it settles, but it is still just
N physical gates in hardware, firing once per clock phase. So the settle
loop uses the uncounted gates.nand_raw(), and count_physical(n) is called
exactly once per invocation to attribute the real gate count, independent
of how many iterations settling took. Every other gate in this file (the
D/enable forming logic, the Bit's Mux, the address decoder) is ordinary
combinational logic with no feedback, so it goes through the normally
counted gates.Not/And/Or/Mux/DMux and needs no special handling.
"""

import gates
from gates import Not, And, Mux, DMux


# ---- 1. SR latch: 2 cross-coupled NAND gates ----

SR_LATCH_GATES = 2  # the two cross-coupled NANDs themselves


def sr_latch(s, r, prev_q, prev_qn, max_iters=16):
    """Cross-coupled NAND SR latch. s/r are active-HIGH: set=1 forces
    Q=1, reset=1 forces Q=0, s=r=0 holds the last value. Returns (q, qn).

    FORBIDDEN INPUT: s=1 and r=1 at the same time. The two core NAND
    gates are then both being forced toward output 1 by their *inverted*
    input (s_bar=0 or r_bar=0 respectively), which breaks the Q/Qn
    complementary invariant real hardware depends on; in a physical
    latch, releasing both lines together makes the final state a race
    between the two gates' propagation delays — undefined. We don't
    special-case it: this simulation has no delay to race on, so it
    settles deterministically at q=qn=1, which is the textbook "invalid"
    state. test_registers.py asserts exactly that (documented, not
    silently avoided).

    Built from the classic 2-gate active-LOW NAND latch via two input
    inverters (s_bar/r_bar), which are ordinary gates — counted
    normally. Only the 2 cross-coupled core gates use the feedback
    gate-counting rule (see count_physical's docstring).
    """
    s_bar = Not(s)   # counted normally — 1 gate
    r_bar = Not(r)   # counted normally — 1 gate

    q, qn = prev_q, prev_qn
    for _ in range(max_iters):
        new_q = gates.nand_raw(s_bar, qn)
        new_qn = gates.nand_raw(r_bar, q)
        if new_q == q and new_qn == qn:
            break
        q, qn = new_q, new_qn
    else:
        raise RuntimeError(
            f"SR latch did not settle within {max_iters} iterations "
            f"(s={s}, r={r}, prev=({prev_q},{prev_qn}))"
        )

    gates.count_physical(SR_LATCH_GATES)
    return q, qn


# ---- 2. Gated D latch: SR latch + enable, D/EN forming logic ----

def d_latch(d, en, prev_q, prev_qn):
    """Transparent while en=1 (q follows d); holds the last value while
    en=0. Built so S and R are never both 1: s = AND(d, en),
    r = AND(NOT(d), en) — exactly one of them can be 1 when en=1, and
    both are 0 when en=0 (hold), so the SR latch's forbidden input is
    structurally unreachable here."""
    not_d = Not(d)
    s = And(d, en)
    r = And(not_d, en)
    return sr_latch(s, r, prev_q, prev_qn)


# ---- 3. Master-slave D flip-flop: two gated D latches, clk-driven ----

class DFF:
    """Edge-triggered 1-bit flip-flop, built from two gated D latches:
    a master (enabled while clk=0, transparent to D) feeding a slave
    (enabled while clk=1, transparent to the master's held value). One
    full tick() runs the clock 0 -> 1 once, so the flip-flop captures
    whatever D was during the "clk=0" phase and makes it visible at Q
    only once the "clk=1" phase completes — the same clock edge a real
    master-slave DFF reacts to, not to D changing on its own.
    """

    def __init__(self):
        # Power up in the (q=0, qn=1) self-consistent state. (0, 0) is
        # NOT a valid SR latch rest state — under hold (s=r=0) it is a
        # perfect zero-delay oscillator that never settles (q and qn
        # would forever flip to match each other then diverge again).
        self.master_q, self.master_qn = 0, 1
        self.slave_q, self.slave_qn = 0, 1

    @property
    def q(self):
        return self.slave_q

    def phase_low(self, d):
        """clk=0: master is transparent (enable=NOT(clk)=1) and samples
        d; the slave's enable=clk=0, so it holds — Q is unaffected."""
        self.master_q, self.master_qn = d_latch(
            d, 1, self.master_q, self.master_qn
        )
        return self.slave_q  # unchanged — proves D alone can't move Q

    def phase_high(self):
        """clk=1: master's enable=NOT(clk)=0, so it now holds whatever
        it last sampled; the slave's enable=clk=1, so it becomes
        transparent and Q takes on the master's held value."""
        self.slave_q, self.slave_qn = d_latch(
            self.master_q, 1, self.slave_q, self.slave_qn
        )
        # master re-evaluated with en=0 so it's charged to the counter
        # for this phase too (it's a real gate, idle or not)
        self.master_q, self.master_qn = d_latch(
            self.master_q, 0, self.master_q, self.master_qn
        )
        return self.slave_q

    def tick(self, d):
        """One full clock cycle (clk 0 -> 1). Matches the rest of the
        codebase's convention that one .tick() call = one clock cycle."""
        self.phase_low(d)
        return self.phase_high()


# ---- 4. Bit: 1-bit cell with a load input, then the 16-bit register ----

class Bit:
    """1-bit register with a load control: Bit(d, load) = DFF(Mux(Q, d,
    load)). When load=0 the DFF is fed its own current output back as
    D, so ticking it is a real gate-level re-capture of the same value
    (hold); when load=1 it captures d. This is the same load-via-Mux
    trick memory.py's behavioural Register expresses as a plain `if`."""

    def __init__(self):
        self.dff = DFF()

    @property
    def value(self):
        return self.dff.q

    def tick(self, load, d):
        mux_out = Mux(self.dff.q, d, load)
        return self.dff.tick(mux_out)


class GateRegister:
    """16-bit register built from 16 Bit cells sharing one load line —
    the gate-built counterpart to memory.py's behavioural Register.
    Same interface: .bits (LSB first) and .tick(load, in_bits)."""

    def __init__(self):
        self.cells = [Bit() for _ in range(16)]

    @property
    def bits(self):
        return [c.value for c in self.cells]

    def tick(self, load, in_bits):
        for cell, bit in zip(self.cells, in_bits):
            cell.tick(load, bit)
        return self.bits


# ---- RAM8: 8 GateRegisters behind a 3-bit address decoder ----

def _demux8(sel3):
    """3-bit select -> 8 one-hot enable lines, built from DMux. sel3 is
    LSB-first (sel3[0] = bit0 ... sel3[2] = bit2)."""
    a, b = DMux(1, sel3[2])          # a: bit2=0 half, b: bit2=1 half
    a0, a1 = DMux(a, sel3[1])
    b0, b1 = DMux(b, sel3[1])
    lines = []
    for half in (a0, a1, b0, b1):
        lines.append(DMux(half, sel3[0]))
    # lines is [(a00,a01), (a10,a11), (b00,b01), (b10,b11)] -> flatten to
    # addresses 0..7 in the order a0,b0,c0,...
    flat = []
    for lo, hi in lines:
        flat.append(lo)
        flat.append(hi)
    return flat  # flat[i] = 1 iff sel3 == i


class RAM8:
    """8-word x 16-bit RAM, gate-built: 8 GateRegisters, addressed by a
    3-bit DMux-based decoder that produces one-hot "load this register"
    lines, muxed back together on read with Mux. This is the proof that
    a NAND-gate register array behaves like real memory; the CPU's main
    256-word RAM (memory.py) stays a behavioural model — RAM8 is not
    wired into the CPU, it exists to be tested against that model.
    """

    def __init__(self):
        self.regs = [GateRegister() for _ in range(8)]

    def read(self, addr3):
        """addr3: 3-bit address, LSB-first. Selects the addressed
        register's 16-bit value by chaining Mux across the one-hot
        enable lines — since exactly one `en` is ever 1, this is really
        an 8-way select, just expressed as 7 nested 2-way ones."""
        enables = _demux8(addr3)
        result = [0] * 16
        for reg, en in zip(self.regs, enables):
            bits = reg.bits
            result = [Mux(result[i], bits[i], en) for i in range(16)]
        return result

    def write(self, addr3, load, in_bits):
        enables = _demux8(addr3)
        for reg, en in zip(self.regs, enables):
            reg.tick(And(load, en), in_bits)
