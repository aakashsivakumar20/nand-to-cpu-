"""
arithmetic.py — Layer 2: Boolean Arithmetic

Half/Full adders -> 16-bit adder -> two's-complement negate/subtract ->
zero-check. This is the "calculator" layer: everything a basic ALU needs,
built only from the gates in gates.py.
"""

from gates import Not16, Xor, And, Or, Not


def half_adder(a, b):
    """Returns (sum, carry) for a single bit."""
    return Xor(a, b), And(a, b)


def full_adder(a, b, c):
    """Returns (sum, carry) for a single bit plus carry-in."""
    s1, c1 = half_adder(a, b)
    s2, c2 = half_adder(s1, c)
    return s2, Or(c1, c2)


def add16(a, b):
    """16-bit ripple-carry adder. a, b: bit-lists, LSB first."""
    result = []
    carry = 0
    for x, y in zip(a, b):
        s, carry = full_adder(x, y, carry)
        result.append(s)
    return result


def int_to_bits(n, width=16):
    """Two's-complement int -> bit-list, LSB first."""
    n = n & ((1 << width) - 1)
    return [(n >> i) & 1 for i in range(width)]


def bits_to_int(bits):
    """Bit-list, LSB first -> signed two's-complement int."""
    n = 0
    for i, b in enumerate(bits):
        n |= (b << i)
    if n >= (1 << (len(bits) - 1)):
        n -= (1 << len(bits))
    return n


def negate16(a):
    """Two's-complement negation: ~a + 1."""
    return add16(Not16(a), int_to_bits(1))


def sub16(a, b):
    """a - b, via a + (-b)."""
    return add16(a, negate16(b))


def is_zero16(a):
    """Returns 1 if every bit of a is 0, else 0."""
    any_one = 0
    for bit in a:
        any_one = Or(any_one, bit)
    return Not(any_one)
