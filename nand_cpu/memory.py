"""
memory.py — Layer 3: Sequential Logic (memory)

Pure gates (Layer 1) have no memory — output depends only on current input.
A Register is the software stand-in for a clocked flip-flop-based register:
call .tick(load, in_bits) once per clock cycle to update it. RAM is an array
of registers addressed by index — this RAM, and this Register class, are a
BEHAVIOURAL MODEL (`self.bits = list(...)` on load, i.e. Python's own
assignment stands in for "remembers a value"), kept as-is for the CPU's
256-word program/data memory because gate-building all 256 words would cost
millions of simulated NAND gates per cycle for no behavioural difference.

registers.py builds the real thing from Nand() gates — SR latch -> D latch
-> master-slave flip-flop -> Bit -> GateRegister (and RAM8, an 8-word gate-
built proof that the construction matches this model exactly). ProgramCounter
below uses that GateRegister internally: the increment/load/reset control
logic here is ordinary combinational code, but the value it latches into is
now held by real gates, not a Python list assignment.
"""

from arithmetic import add16, int_to_bits
from registers import GateRegister


class Register:
    """16-bit register. Holds its value until told to load a new one.
    Behavioural model — see the module docstring. Used by RAM (and still
    available for anything that doesn't need the gate-built version)."""

    def __init__(self):
        self.bits = [0] * 16

    def tick(self, load, in_bits):
        if load:
            self.bits = list(in_bits)
        return self.bits


class RAM:
    """A flat array of 16-bit registers, addressed by index. Behavioural
    model — see the module docstring; registers.RAM8 is the gate-built
    proof that this is a faithful stand-in, on an 8-word scale."""

    def __init__(self, size=256):
        self.regs = [Register() for _ in range(size)]

    def read(self, addr):
        return self.regs[addr].bits

    def write(self, addr, load, in_bits):
        self.regs[addr].tick(load, in_bits)


class ProgramCounter:
    """Gate-built register (registers.GateRegister) with reset / load /
    increment control, like the Hack PC. The control logic (which value
    to latch) is ordinary combinational code; the latching itself is now
    done by 16 real NAND-built flip-flops, not a Python list assignment."""

    def __init__(self):
        self.reg = GateRegister()

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
