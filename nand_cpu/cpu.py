"""
cpu.py — Layer 4: the CPU

Wires the ALU (arithmetic.py), memory (memory.py), and the custom
instruction set (assembler.py) together into a fetch-decode-execute
loop that runs a whole program by itself, cycle by cycle.

Every executed instruction logs: cycle number, PC, instruction, ACC
before/after, and how many NAND gates fired during that cycle (this
is the raw data the visualizer turns into a report).
"""

import gates
from arithmetic import add16, sub16, is_zero16, int_to_bits, bits_to_int
from memory import Register, RAM, ProgramCounter
from assembler import MNEMONICS


class CPU:
    def __init__(self, program, ram_size=256, trace=False):
        self.ram = RAM(ram_size)
        for i, instr in enumerate(program):
            self.ram.write(i, 1, int_to_bits(instr))

        self.acc = Register()
        self.pc = ProgramCounter()
        self.halted = False
        self.trace = trace
        self.cycle = 0
        self.log = []  # full execution trace, used by the visualizer

    def step(self):
        if self.halted:
            return False

        pc_val = bits_to_int(self.pc.reg.bits) & 0xFFFF
        instr = bits_to_int(self.ram.read(pc_val)) & 0xFFFF
        opcode = (instr >> 12) & 0xF
        operand = instr & 0xFFF

        gates_before = gates.GATE_COUNT
        acc_before = bits_to_int(self.acc.bits)

        jumped, jump_target = False, 0

        if opcode == 0:      # NOP
            pass
        elif opcode == 1:    # LOADI
            self.acc.tick(1, int_to_bits(operand))
        elif opcode == 2:    # LOAD
            self.acc.tick(1, self.ram.read(operand))
        elif opcode == 3:    # STORE
            self.ram.write(operand, 1, self.acc.bits)
        elif opcode == 4:    # ADD
            self.acc.tick(1, add16(self.acc.bits, self.ram.read(operand)))
        elif opcode == 5:    # SUB
            self.acc.tick(1, sub16(self.acc.bits, self.ram.read(operand)))
        elif opcode == 6:    # JUMP
            jumped, jump_target = True, operand
        elif opcode == 7:    # JZ
            if is_zero16(self.acc.bits):
                jumped, jump_target = True, operand
        elif opcode == 8:    # JNZ
            if not is_zero16(self.acc.bits):
                jumped, jump_target = True, operand
        elif opcode == 9:    # HALT
            self.halted = True

        if not self.halted:
            if jumped:
                self.pc.tick(1, 0, 0, int_to_bits(jump_target))
            else:
                self.pc.tick(0, 1, 0, int_to_bits(0))

        gates_used = gates.GATE_COUNT - gates_before
        acc_after = bits_to_int(self.acc.bits)
        mnemonic = MNEMONICS.get(opcode, '???')

        record = {
            'cycle': self.cycle, 'pc': pc_val, 'mnemonic': mnemonic,
            'operand': operand, 'acc_before': acc_before,
            'acc_after': acc_after, 'gates_used': gates_used,
        }
        self.log.append(record)

        if self.trace:
            print(f"cycle {self.cycle:3d} | PC={pc_val:3d} | {mnemonic:6s} {operand:4d} "
                  f"| ACC {acc_before:6d} -> {acc_after:6d} | gates used: {gates_used}")

        self.cycle += 1
        return not self.halted

    def run(self, max_cycles=100000):
        while self.step() and self.cycle < max_cycles:
            pass
        return bits_to_int(self.acc.bits)
