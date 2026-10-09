"""
test_gates.py — sanity checks that every layer behaves correctly,
starting from raw NAND truth tables up to 16-bit addition.

Run: python3 test_gates.py
"""

from gates import Nand, Not, And, Or, Xor, Mux, DMux
from arithmetic import add16, sub16, is_zero16, int_to_bits, bits_to_int


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


if __name__ == "__main__":
    test_nand()
    test_derived_gates()
    test_arithmetic()
    print("\nAll layers verified: NAND -> gates -> arithmetic all correct.")
