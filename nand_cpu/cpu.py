"""
cpu.py — Layer 4: the CPU

Wires the ALU (arithmetic.py), memory (memory.py), and the custom
instruction set (assembler.py) together into a fetch-decode-execute
loop that runs a whole program by itself, cycle by cycle.

Every executed instruction logs: cycle number, PC, instruction, ACC
before/after, the Z/N/V status flags, and how many NAND gates fired
during that cycle (this is the raw data the visualizer turns into a
report).
"""

import gates
from arithmetic import add16, sub16, add16_flags, sub16_flags, is_zero16, int_to_bits, bits_to_int
from memory import RAM, ProgramCounter
from registers import GateRegister
from assembler import MNEMONICS


class CPU:
    def __init__(self, program, ram_size=256, trace=False):
        self.ram = RAM(ram_size)
        for i, instr in enumerate(program):
            self.ram.write(i, 1, int_to_bits(instr))

        # ACC, the program counter (inside ProgramCounter) and the
        # instruction register are gate-built (registers.GateRegister):
        # 16 real NAND-chained flip-flops each, not a Python list
        # assignment. The 256-word RAM stays the behavioural model
        # (see memory.py's docstring) — gate-building all of it would
        # cost millions of simulated gates per cycle for no behavioural
        # difference; registers.RAM8 is the gate-built proof instead.
        self.acc = GateRegister()
        self.ir = GateRegister()
        self.pc = ProgramCounter()
        self.halted = False
        self.trace = trace
        self.cycle = 0
        self.log = []  # full execution trace, used by the visualizer
        # Status register: set only by ADD/SUB/CMP, like a real ALU flags
        # register. Z = zero, N = sign bit, V = signed (two's-complement)
        # overflow.
        self.flags = {'z': 0, 'n': 0, 'v': 0}

    def step(self):
        if self.halted:
            return False

        # Snapshot the gate counter before anything this cycle touches a
        # gate — including fetch — so gates_used below attributes every
        # gate fired this cycle (IR load included) to this cycle's log
        # entry, not to the next one or to no entry at all.
        gates_before = gates.GATE_COUNT

        pc_val = bits_to_int(self.pc.reg.bits) & 0xFFFF
        # Fetch: the instruction register always loads every cycle (real
        # hardware's IR captures whatever the memory bus is driving on
        # every fetch, unconditionally) — decode reads from the IR's own
        # gate-built flip-flops, not straight off the RAM read.
        self.ir.tick(1, self.ram.read(pc_val))
        instr = bits_to_int(self.ir.bits) & 0xFFFF
        opcode = (instr >> 12) & 0xF
        operand = instr & 0xFFF

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
        elif opcode == 4:    # ADD — writes ACC and sets Z/N/V
            result, z, n, v = add16_flags(self.acc.bits, self.ram.read(operand))
            self.acc.tick(1, result)
            self.flags = {'z': z, 'n': n, 'v': v}
        elif opcode == 5:    # SUB — writes ACC and sets Z/N/V
            result, z, n, v = sub16_flags(self.acc.bits, self.ram.read(operand))
            self.acc.tick(1, result)
            self.flags = {'z': z, 'n': n, 'v': v}
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
        elif opcode == 10:   # JLT: signed less-than (N XOR V) from the last ADD/SUB/CMP;
                             # after CMP addr this means ACC < RAM[addr]
            if gates.Xor(self.flags['n'], self.flags['v']):
                jumped, jump_target = True, operand
        elif opcode == 11:   # JOV: signed overflow set by the last ADD/SUB/CMP
            if self.flags['v']:
                jumped, jump_target = True, operand
        elif opcode == 12:   # CMP — same as SUB but ACC is left unchanged
            _, z, n, v = sub16_flags(self.acc.bits, self.ram.read(operand))
            self.flags = {'z': z, 'n': n, 'v': v}

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
            'z': self.flags['z'], 'n': self.flags['n'], 'v': self.flags['v'],
        }
        self.log.append(record)

        if self.trace:
            print(f"cycle {self.cycle:3d} | PC={pc_val:3d} | {mnemonic:6s} {operand:4d} "
                  f"| ACC {acc_before:6d} -> {acc_after:6d} "
                  f"| Z={self.flags['z']} N={self.flags['n']} V={self.flags['v']} "
                  f"| gates used: {gates_used}")

        self.cycle += 1
        return not self.halted

    def run(self, max_cycles=100000):
        while self.step() and self.cycle < max_cycles:
            pass
        return bits_to_int(self.acc.bits)
