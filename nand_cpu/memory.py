"""
memory.py — Layer 3: Sequential Logic (memory)

Pure gates (Layer 1) have no memory — output depends only on current input.
A Register is the software stand-in for a clocked flip-flop-based register:
call .tick(load, in_bits) once per clock cycle to update it. RAM is an array
of registers addressed by index. ProgramCounter is a register that knows how
to increment, jump, or reset.
"""

from arithmetic import add16, int_to_bits


class Register:
    """16-bit register. Holds its value until told to load a new one."""

    def __init__(self):
        self.bits = [0] * 16

    def tick(self, load, in_bits):
        if load:
            self.bits = list(in_bits)
        return self.bits


class RAM:
    """A flat array of 16-bit registers, addressed by index."""

    def __init__(self, size=256):
        self.regs = [Register() for _ in range(size)]

    def read(self, addr):
        return self.regs[addr].bits

    def write(self, addr, load, in_bits):
        self.regs[addr].tick(load, in_bits)


class ProgramCounter:
    """Register with reset / load / increment control, like the Hack PC."""

    def __init__(self):
        self.reg = Register()

    def tick(self, load, inc, reset, in_bits):
        if reset:
            new_val = int_to_bits(0)
        elif load:
            new_val = in_bits
        elif inc:
            new_val = add16(self.reg.bits, int_to_bits(1))
        else:
            new_val = self.reg.bits
        self.reg.tick(1, new_val)
        return self.reg.bits
