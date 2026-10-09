"""
test_registers.py — sanity checks for the NAND-built memory hierarchy in
registers.py: SR latch -> gated D latch -> master-slave DFF -> Bit ->
GateRegister -> RAM8.

Run: python3 test_registers.py
"""

import random

import gates
from arithmetic import int_to_bits, bits_to_int
from registers import sr_latch, d_latch, DFF, Bit, GateRegister, RAM8


def check(label, actual, expected):
    status = "PASS" if actual == expected else "FAIL"
    print(f"[{status}] {label}: got {actual}, expected {expected}")
    assert actual == expected, label


def test_sr_latch_set_reset_hold():
    q, qn = 0, 1  # power-up rest state
    q, qn = sr_latch(1, 0, q, qn)
    check("SR latch set -> q", q, 1)
    check("SR latch set -> qn", qn, 0)

    q, qn = sr_latch(0, 0, q, qn)
    check("SR latch hold after set -> q", q, 1)
    check("SR latch hold after set -> qn", qn, 0)

    q, qn = sr_latch(0, 1, q, qn)
    check("SR latch reset -> q", q, 0)
    check("SR latch reset -> qn", qn, 1)

    q, qn = sr_latch(0, 0, q, qn)
    check("SR latch hold after reset -> q", q, 0)
    check("SR latch hold after reset -> qn", qn, 1)


def test_sr_latch_forbidden_input():
    # Documented, not avoided: s=r=1 drives both core NANDs' inverted
    # input to 0, forcing both outputs to 1 — breaking the Q/Qn
    # complementary invariant. A real latch's resolution on release is a
    # propagation-delay race (undefined); this zero-delay simulation
    # settles deterministically at q=qn=1.
    q, qn = sr_latch(1, 1, 0, 1)
    check("SR latch forbidden input q", q, 1)
    check("SR latch forbidden input qn", qn, 1)


def test_d_latch_transparent_and_hold():
    q, qn = 0, 1
    q, qn = d_latch(1, 1, q, qn)  # en=1 -> transparent, follows d
    check("D latch transparent d=1", q, 1)
    q, qn = d_latch(0, 1, q, qn)
    check("D latch transparent d=0", q, 0)
    q, qn = d_latch(1, 0, q, qn)  # en=0 -> holds, ignores d
    check("D latch holds through d change", q, 0)


def test_dff_captures_only_on_clock_edge():
    dff = DFF()
    check("DFF initial q", dff.q, 0)

    # clk=0 phase: master samples D=1, but Q must NOT move yet — proof
    # that this is edge-triggered, not level-sensitive.
    dff.phase_low(1)
    check("DFF q unaffected by phase_low alone", dff.q, 0)

    # clk=1 phase: the edge completes, Q now reflects the sampled D.
    dff.phase_high()
    check("DFF q after the clock edge completes", dff.q, 1)

    # Changing D without a new clk=0->1 edge must not move Q again.
    check("DFF still holding without a new edge", dff.q, 1)

    # A full tick() is one clk 0->1 edge.
    check("DFF tick(0)", dff.tick(0), 0)
    check("DFF tick(1)", dff.tick(1), 1)


def test_bit_write_and_hold():
    bit = Bit()
    check("Bit load=1 d=1", bit.tick(1, 1), 1)
    check("Bit load=0 holds", bit.tick(0, 0), 1)
    check("Bit load=1 d=0", bit.tick(1, 0), 0)
    check("Bit load=0 holds (0)", bit.tick(0, 1), 0)


def test_gate_register_write_and_hold():
    reg = GateRegister()
    reg.tick(1, int_to_bits(0xBEEF))
    check("GateRegister load", bits_to_int(reg.bits) & 0xFFFF, 0xBEEF)

    reg.tick(0, int_to_bits(0))  # load=0 -> must ignore the 0 and hold
    check("GateRegister hold", bits_to_int(reg.bits) & 0xFFFF, 0xBEEF)

    reg.tick(1, int_to_bits(0x1234))
    check("GateRegister second load", bits_to_int(reg.bits) & 0xFFFF, 0x1234)


def test_ram8_matches_behavioural_model():
    random.seed(42)
    ram8 = RAM8()
    model = [0] * 8

    for step in range(300):
        addr = random.randint(0, 7)
        if random.random() < 0.5:
            val = random.randint(0, 65535)
            ram8.write(int_to_bits(addr, 3), 1, int_to_bits(val))
            model[addr] = val & 0xFFFF
        else:
            ram8.write(int_to_bits(addr, 3), 0, int_to_bits(0))  # no-op

        for a in range(8):
            got = bits_to_int(ram8.read(int_to_bits(a, 3))) & 0xFFFF
            check(f"RAM8 vs model @ step {step} addr {a}", got, model[a])


def report_gate_costs():
    gates.reset_gate_count()
    sr_latch(1, 0, 0, 1)
    sr_cost = gates.GATE_COUNT

    gates.reset_gate_count()
    DFF().tick(1)
    dff_cost = gates.GATE_COUNT

    gates.reset_gate_count()
    GateRegister().tick(1, int_to_bits(0xFFFF))
    reg_cost = gates.GATE_COUNT

    gates.reset_gate_count()
    ram8 = RAM8()
    ram8.write(int_to_bits(0, 3), 1, int_to_bits(0xFFFF))
    ram8_write_cost = gates.GATE_COUNT

    gates.reset_gate_count()
    ram8.read(int_to_bits(0, 3))
    ram8_read_cost = gates.GATE_COUNT

    print()
    print("Measured gate costs:")
    print(f"  1 SR latch call:          {sr_cost}")
    print(f"  1 DFF tick:               {dff_cost}")
    print(f"  1 16-bit GateRegister tick: {reg_cost}")
    print(f"  1 RAM8 write:             {ram8_write_cost}")
    print(f"  1 RAM8 read:              {ram8_read_cost}")


if __name__ == "__main__":
    test_sr_latch_set_reset_hold()
    test_sr_latch_forbidden_input()
    test_d_latch_transparent_and_hold()
    test_dff_captures_only_on_clock_edge()
    test_bit_write_and_hold()
    test_gate_register_write_and_hold()
    test_ram8_matches_behavioural_model()
    report_gate_costs()
    print("\nAll register layers verified: NAND -> latch -> flip-flop -> register -> RAM8.")
