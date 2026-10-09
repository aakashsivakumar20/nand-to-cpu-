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
    print("\nAll layers verified: NAND -> gates -> arithmetic all correct.")
