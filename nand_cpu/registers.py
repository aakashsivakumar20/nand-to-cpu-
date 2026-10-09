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
Bit's Mux, the address decoder) is ordinary combinational logic with no
feedback, so it goes through the normally counted gates.Nand/Not/And/
Or/Mux/DMux and needs no special handling.

The SR latch is the textbook 2-gate active-LOW circuit directly (no
input inversion — see sr_latch); the gated D latch is the textbook
4-NAND circuit directly (see d_latch), not a separate SR latch fed by
extra D/enable-forming gates. The master-slave DFF is exactly two of
those D latches plus one inverter for the clock, each physical gate
counted exactly once per tick() — see DFF's docstring for why phase_high
does not re-run the master's gates a second time.
"""

import gates
from gates import Nand, Not, And, Mux, DMux


# ---- 1. SR latch: the textbook 2-gate active-LOW circuit, directly ----

SR_LATCH_GATES = 2  # the two cross-coupled NANDs — nothing else


def sr_latch(s_bar, r_bar, prev_q, prev_qn, max_iters=16):
    """Cross-coupled NAND SR latch, ACTIVE-LOW inputs — the textbook
    2-gate circuit taken directly, with no input inversion:
        q  = NAND(s_bar, qn)
        qn = NAND(r_bar, q)
    s_bar=0 forces q=1 (set), r_bar=0 forces q=0 (reset), s_bar=r_bar=1
    holds the last value. Returns (q, qn).

    FORBIDDEN INPUT: s_bar=0 and r_bar=0 at the same time. Both core
    NAND gates are then forced toward output 1 by their own 0 input,
    which breaks the Q/Qn complementary invariant real hardware depends
    on; in a physical latch, releasing both lines together makes the
    final state a race between the two gates' propagation delays —
    undefined. We don't special-case it: this simulation has no delay to
    race on, so it settles deterministically at q=qn=1, which is the
    textbook "invalid" state. test_registers.py asserts exactly that
    (documented, not silently avoided).

    GATE COUNTING: this is the ENTIRE physical circuit — just the 2
    cross-coupled NANDs, counted once per call via count_physical,
    independent of how many iterations settling took (see
    count_physical's docstring). No input-forming gates here at all —
    callers that want active-HIGH semantics invert before calling, and
    that inversion is their own, separately-counted gate (see d_latch,
    which instead builds s_bar/r_bar straight from NAND gates and never
    needs an active-high view in the first place).
    """
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
            f"(s_bar={s_bar}, r_bar={r_bar}, prev=({prev_q},{prev_qn}))"
        )

    gates.count_physical(SR_LATCH_GATES)
    return q, qn


# ---- 2. Gated D latch: the textbook 4-NAND circuit ----

def d_latch(d, en, prev_q, prev_qn):
    """Transparent while en=1 (q follows d); holds the last value while
    en=0. The textbook 4-NAND gated D latch, taken directly:
        a  = NAND(d, en)
        b  = NAND(a, en)
        q  = NAND(a, qn)
        qn = NAND(b, q)
    The last two ARE the active-low SR latch core above, fed s_bar=a,
    r_bar=b — a and b can never both be 0 (when en=0 both are forced to
    1; when en=1 exactly one of them is 0, depending on d), so the SR
    latch's forbidden input is structurally unreachable here. a and b
    depend only on d/en, not on the feedback, so they're computed once
    (ordinary counted NANDs) outside the settle loop; only the q/qn pair
    needs iterating.
    """
    a = Nand(d, en)   # counted normally — 1 gate
    b = Nand(a, en)   # counted normally — 1 gate
    return sr_latch(a, b, prev_q, prev_qn)


# ---- 3. Master-slave D flip-flop: two gated D latches, clk-driven ----

class DFF:
    """Edge-triggered 1-bit flip-flop: a master latch (enabled while
    clk=0, transparent to D) feeding a slave latch (enabled while clk=1,
    transparent to the master's held value). One full tick() runs the
    clock 0 -> 1 once, so the flip-flop captures whatever D was during
    the "clk=0" phase and makes it visible at Q only once the "clk=1"
    phase completes — the same clock edge a real master-slave DFF reacts
    to, not to D changing on its own.

    GATE COUNTING: a master-slave DFF is physically two latches plus one
    inverter that derives the master's enable from the clock — 2*4 + 1 = 9
    gates, counted exactly once per tick(). The one inverter fires in
    phase_low (NOT(clk=0) -> master_en=1, opening the master to sample
    d). phase_high does NOT re-run the master's gates a second time: by
    the time the clock reaches 1, the master's enable would be NOT(1)=0
    (closed) and its stored value simply isn't re-derived — a closed
    latch holding is not a second physical evaluation of that latch, so
    re-calling d_latch for it here would double-count the same 4 gates.
    The slave's enable is the clock signal directly (no inverter needed
    for it), so phase_high spends exactly one d_latch call (4 gates) on
    the slave and nothing more.
    """

    def __init__(self):
        # Power up in the (q=0, qn=1) self-consistent state. (0, 0) is
        # NOT a valid SR latch rest state — under hold (s_bar=r_bar=1)
        # it is a perfect zero-delay oscillator that never settles (q
        # and qn would forever flip to match each other then diverge).
        self.master_q, self.master_qn = 0, 1
        self.slave_q, self.slave_qn = 0, 1

    @property
    def q(self):
        return self.slave_q

    def phase_low(self, d):
        """clk=0: the DFF's one clock inverter fires here (NOT(0)=1),
        opening the master, which then samples d. The slave's enable is
        clk=0 directly (closed), so it isn't touched — Q is unaffected,
        proving D alone (without a clock edge) can't move Q."""
        master_en = Not(0)   # the ONE inverter this DFF spends per tick
        self.master_q, self.master_qn = d_latch(
            d, master_en, self.master_q, self.master_qn
        )
        return self.slave_q

    def phase_high(self):
        """clk=1: the slave's enable is clk=1 directly (open) — it
        captures whatever the master is currently holding. The master
        itself is not re-evaluated here (see the class docstring)."""
        self.slave_q, self.slave_qn = d_latch(
            self.master_q, 1, self.slave_q, self.slave_qn
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
