"""
test_gates.py — sanity checks that every layer behaves correctly,
starting from raw NAND truth tables up to 16-bit addition.

Run: python3 test_gates.py
"""

from gates import Nand, Not, And, Or, Xor, Mux, DMux
from arithmetic import (
    add16, sub16, add16_flags, sub16_flags, is_zero16, int_to_bits, bits_to_int,
)
from assembler import assemble
from cpu import CPU


def check(label, actual, expected):
    status = "PASS" if actual == expected else "FAIL"
    print(f"[{status}] {label}: got {actual}, expected {expected}")
    assert actual == expected, label


def test_nand():
    check("NAND(0,0)", Nand(0, 0), 1)
    check("NAND(0,1)", Nand(0, 1), 1)
    check("NAND(1,0)", Nand(1, 0), 1)
    check("NAND(1,1)", Nand(1, 1), 0)


def test_derived_gates():
    check("NOT(0)", Not(0), 1)
    check("NOT(1)", Not(1), 0)
    check("AND(1,1)", And(1, 1), 1)
    check("AND(1,0)", And(1, 0), 0)
    check("OR(0,0)", Or(0, 0), 0)
    check("OR(0,1)", Or(0, 1), 1)
    check("XOR(1,1)", Xor(1, 1), 0)
    check("XOR(1,0)", Xor(1, 0), 1)
    check("MUX(5-ish a=1,b=0,sel=0)", Mux(1, 0, 0), 1)
    check("MUX(a=1,b=0,sel=1)", Mux(1, 0, 1), 0)
    check("DMUX(1,sel=0)", DMux(1, 0), (1, 0))
    check("DMUX(1,sel=1)", DMux(1, 1), (0, 1))


def test_arithmetic():
    a, b = int_to_bits(7), int_to_bits(5)
    check("7 + 5", bits_to_int(add16(a, b)), 12)

    a, b = int_to_bits(20), int_to_bits(8)
    check("20 - 8", bits_to_int(sub16(a, b)), 12)

    a, b = int_to_bits(3), int_to_bits(-3)
    check("3 + (-3)", bits_to_int(add16(a, b)), 0)

    check("is_zero16(0)", is_zero16(int_to_bits(0)), 1)
    check("is_zero16(5)", is_zero16(int_to_bits(5)), 0)


def test_flags():
    """N/Z/V on ADD and SUB, built from gates in add16_flags/sub16_flags."""
    # ADD: ordinary positive sum — no flags set
    r, z, n, v = add16_flags(int_to_bits(100), int_to_bits(50))
    check("ADD 100+50 result", bits_to_int(r), 150)
    check("ADD 100+50 Z", z, 0)
    check("ADD 100+50 N", n, 0)
    check("ADD 100+50 V", v, 0)

    # ADD: signed overflow — 32767 + 1 wraps to -32768
    r, z, n, v = add16_flags(int_to_bits(32767), int_to_bits(1))
    check("ADD 32767+1 result", bits_to_int(r), -32768)
    check("ADD 32767+1 Z", z, 0)
    check("ADD 32767+1 N", n, 1)
    check("ADD 32767+1 V", v, 1)

    # ADD: result is exactly zero
    r, z, n, v = add16_flags(int_to_bits(5), int_to_bits(-5))
    check("ADD 5+(-5) Z", z, 1)
    check("ADD 5+(-5) N", n, 0)
    check("ADD 5+(-5) V", v, 0)

    # SUB: ordinary difference — no flags set
    r, z, n, v = sub16_flags(int_to_bits(20), int_to_bits(8))
    check("SUB 20-8 result", bits_to_int(r), 12)
    check("SUB 20-8 Z", z, 0)
    check("SUB 20-8 N", n, 0)
    check("SUB 20-8 V", v, 0)

    # SUB: result is negative -> N set, no overflow
    r, z, n, v = sub16_flags(int_to_bits(3), int_to_bits(8))
    check("SUB 3-8 result", bits_to_int(r), -5)
    check("SUB 3-8 N", n, 1)
    check("SUB 3-8 V", v, 0)

    # SUB: signed overflow — -32768 - 1 wraps to 32767
    r, z, n, v = sub16_flags(int_to_bits(-32768), int_to_bits(1))
    check("SUB -32768-1 result", bits_to_int(r), 32767)
    check("SUB -32768-1 N", n, 0)
    check("SUB -32768-1 V", v, 1)


def test_cmp_leaves_acc_unchanged():
    program = assemble("""
        LOADI 10
        STORE 0
        LOADI 7
        CMP 0
        HALT
    """.strip().split('\n'))
    cpu = CPU(program)
    result = cpu.run()
    check("CMP leaves ACC unchanged", result, 7)
    check("CMP sets N (7-10 < 0)", cpu.flags['n'], 1)
    check("CMP sets Z false", cpu.flags['z'], 0)


def test_jlt_branch():
    def jlt_program(acc_val, cmp_addr_val):
        # LOADI acc_val; STORE 0 <- cmp_addr_val; LOADI acc_val; CMP 0; JLT LESS; LOADI 111; HALT; LESS: LOADI 222; HALT
        return assemble(f"""
            LOADI {cmp_addr_val}
            STORE 0
            LOADI {acc_val}
            CMP 0
            JLT LESS
            LOADI 111
            HALT
            LESS:
            LOADI 222
            HALT
        """.strip().split('\n'))

    # 10 >= 5 -> JLT not taken
    cpu = CPU(jlt_program(10, 5))
    result = cpu.run()
    check("JLT not taken (10 vs 5)", result, 111)

    # 3 < 5 -> JLT taken
    cpu = CPU(jlt_program(3, 5))
    result = cpu.run()
    check("JLT taken (3 vs 5)", result, 222)


def test_jov_branch():
    # LOADI's operand is only 12 bits wide (max 4095), so 32767 has to be
    # built up on-CPU by doubling (4095*8 + 7 = 32767) before the final
    # ADD 1 that overflows it to -32768.
    program = assemble("""
        LOADI 4095
        STORE 0
        LOAD 0
        ADD 0
        STORE 0
        LOAD 0
        ADD 0
        STORE 0
        LOAD 0
        ADD 0
        STORE 0
        LOADI 7
        STORE 1
        LOAD 0
        ADD 1
        STORE 0
        LOADI 1
        STORE 2
        LOAD 0
        ADD 2
        JOV OVER
        LOADI 111
        HALT
        OVER:
        LOADI 222
        HALT
    """.strip().split('\n'))
    cpu = CPU(program)
    result = cpu.run()
    check("JOV taken on 32767+1", result, 222)


def divide_program(a, b):
    """The real remainder-vs-divisor loop: while remainder >= divisor:
    remainder -= divisor; quotient++ — built from LOAD/CMP/JLT/SUB/STORE,
    mirroring the JS natural-language generator's genDivide exactly."""
    return assemble(f"""
        LOADI {a}
        STORE 0
        LOADI {b}
        STORE 1
        LOADI 0
        STORE 2
        LOADI 1
        STORE 3
        LOOP:
        LOAD 0
        CMP 1
        JLT END
        SUB 1
        STORE 0
        LOAD 2
        ADD 3
        STORE 2
        JUMP LOOP
        END:
        LOAD 2
        HALT
    """.strip().split('\n'))


def test_division_loop():
    cpu = CPU(divide_program(20, 3))
    quotient = cpu.run()
    remainder = bits_to_int(cpu.ram.read(0))
    check("20 / 3 quotient", quotient, 6)
    check("20 / 3 remainder", remainder, 2)

    cpu = CPU(divide_program(7, 7))
    quotient = cpu.run()
    remainder = bits_to_int(cpu.ram.read(0))
    check("7 / 7 quotient", quotient, 1)
    check("7 / 7 remainder", remainder, 0)

    cpu = CPU(divide_program(5, 9))
    quotient = cpu.run()
    remainder = bits_to_int(cpu.ram.read(0))
    check("5 / 9 quotient", quotient, 0)
    check("5 / 9 remainder", remainder, 5)


def sum_program(n):
    """Sum 1..n via the same counting loop as demo.py's sum 1..10."""
    return assemble(f"""
        LOADI {n}
        STORE 0
        LOADI 0
        STORE 1
        LOADI 1
        STORE 2
        LOOP:
        LOAD 1
        ADD 0
        STORE 1
        LOAD 0
        SUB 2
        STORE 0
        JNZ LOOP
        LOAD 1
        HALT
    """.strip().split('\n'))


def test_sum_overflow_flag():
    cpu = CPU(sum_program(255))
    result = cpu.run()
    overflowed = any(r['v'] for r in cpu.log)
    check("sum 1..255 result", result, 32640)
    check("sum 1..255 never overflows", overflowed, False)

    cpu = CPU(sum_program(300))
    result = cpu.run()
    overflowed = any(r['v'] for r in cpu.log)
    check("sum 1..300 result (wrapped)", result, 45150 - 65536)
    check("sum 1..300 overflow flag raised", overflowed, True)


# ---- per-instruction gate-cost table, measured independently of any
# real program, then checked against the real programs' own traces ----

# Mnemonics that branch — everything else has exactly one cost; these
# have a taken/not-taken split (except JUMP, which is unconditional and
# so only ever has the one "taken" cost).
BRANCH_MNEMONICS = {'JUMP', 'JZ', 'JNZ', 'JLT', 'JOV'}


def measure_instruction_costs():
    """Runs small, dedicated probe programs — none of which share this
    file's demo programs — and returns {(mnemonic, taken_or_None): gates}.
    taken_or_None is None for every non-branching mnemonic and for JUMP
    (unconditional, so it only has one cost), else True/False."""

    def first_cost(src, mnemonic):
        cpu = CPU(assemble(src.strip().split('\n')))
        cpu.run()
        for row in cpu.log:
            if row['mnemonic'] == mnemonic:
                return row['gates_used']
        raise AssertionError(f"{mnemonic} never executed in probe")

    def last_cost(src):
        cpu = CPU(assemble(src.strip().split('\n')))
        cpu.run()
        return cpu.log[-2]['gates_used']  # the instruction right before HALT

    costs = {}
    costs[('NOP', None)] = first_cost("NOP\nHALT", 'NOP')
    costs[('LOADI', None)] = first_cost("LOADI 5\nHALT", 'LOADI')
    costs[('LOAD', None)] = first_cost("LOADI 5\nSTORE 50\nLOAD 50\nHALT", 'LOAD')
    costs[('STORE', None)] = first_cost("LOADI 5\nSTORE 50\nHALT", 'STORE')
    costs[('ADD', None)] = first_cost(
        "LOADI 5\nSTORE 50\nLOADI 3\nSTORE 51\nLOAD 50\nADD 51\nHALT", 'ADD')
    costs[('SUB', None)] = first_cost(
        "LOADI 5\nSTORE 50\nLOADI 3\nSTORE 51\nLOAD 50\nSUB 51\nHALT", 'SUB')
    costs[('CMP', None)] = first_cost(
        "LOADI 5\nSTORE 50\nLOADI 3\nSTORE 51\nLOAD 50\nCMP 51\nHALT", 'CMP')
    halt_cpu = CPU(assemble(['NOP', 'HALT']))
    halt_cpu.run()
    costs[('HALT', None)] = halt_cpu.log[1]['gates_used']

    costs[('JUMP', None)] = last_cost("JUMP 2\nHALT\nHALT")

    costs[('JLT', True)] = last_cost(
        "LOADI 5\nSTORE 50\nLOADI 2\nCMP 50\nJLT 6\nHALT\nHALT")
    costs[('JLT', False)] = first_cost(
        "LOADI 5\nSTORE 50\nLOADI 8\nCMP 50\nJLT 6\nHALT\nHALT", 'JLT')

    costs[('JZ', True)] = first_cost("LOADI 0\nJZ 3\nHALT\nHALT", 'JZ')
    costs[('JZ', False)] = first_cost("LOADI 5\nJZ 3\nHALT\nHALT", 'JZ')
    costs[('JNZ', True)] = first_cost("LOADI 5\nJNZ 3\nHALT\nHALT", 'JNZ')
    costs[('JNZ', False)] = first_cost("LOADI 0\nJNZ 99\nHALT", 'JNZ')

    # JOV taken: build 32767 on-CPU (4095*8+7) since LOADI's operand is
    # only 12 bits, then one more ADD overflows it to -32768.
    costs[('JOV', True)] = last_cost("""
LOADI 4095
STORE 50
LOAD 50
ADD 50
STORE 50
LOAD 50
ADD 50
STORE 50
LOAD 50
ADD 50
STORE 50
LOADI 7
STORE 51
LOAD 50
ADD 51
STORE 50
LOADI 1
STORE 52
LOAD 50
ADD 52
JOV 22
HALT
HALT""")
    costs[('JOV', False)] = first_cost(
        "LOADI 5\nSTORE 50\nLOADI 3\nSTORE 51\nLOAD 50\nADD 51\nJOV 99\nHALT", 'JOV')

    return costs


def predicted_total(cost_table, log):
    """Sums cost_table[(mnemonic, taken)] over every row in a real
    program's trace, inferring taken/not-taken from consecutive PCs:
    a branch "took" iff the next row's PC isn't this row's PC + 1."""
    total = 0
    for i, row in enumerate(log):
        mnemonic = row['mnemonic']
        if mnemonic in BRANCH_MNEMONICS and mnemonic != 'JUMP':
            next_pc = log[i + 1]['pc'] if i + 1 < len(log) else None
            taken = (next_pc is not None) and (next_pc != row['pc'] + 1)
            key = (mnemonic, taken)
        else:
            key = (mnemonic, None)
        total += cost_table[key]
    return total


def test_per_instruction_cost_table_matches_real_programs():
    cost_table = measure_instruction_costs()

    programs = {
        'sum 1..10': sum_program(10),
        'sum 1..300': sum_program(300),
        '20/3': divide_program(20, 3),
        '5/9': divide_program(5, 9),
    }
    for name, program in programs.items():
        cpu = CPU(program)
        cpu.run()
        actual_total = sum(r['gates_used'] for r in cpu.log)
        predicted = predicted_total(cost_table, cpu.log)
        check(f"per-instruction cost table reproduces total for {name}",
              predicted, actual_total)


if __name__ == "__main__":
    test_nand()
    test_derived_gates()
    test_arithmetic()
    test_flags()
    test_cmp_leaves_acc_unchanged()
    test_jlt_branch()
    test_jov_branch()
    test_division_loop()
    test_sum_overflow_flag()
    test_per_instruction_cost_table_matches_real_programs()
    print("\nAll layers verified: NAND -> gates -> arithmetic all correct.")
