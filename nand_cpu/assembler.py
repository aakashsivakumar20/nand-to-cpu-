"""
assembler.py — custom instruction set + a tiny two-pass assembler.

Instruction format (16 bits): [ opcode: 4 bits | operand: 12 bits ]
This is our own, self-designed ISA (deliberately smaller than the
standard course ISA) — an accumulator machine: one working register
(ACC), everything else lives in RAM.
"""

OPCODES = {
    'NOP':   0,  # do nothing
    'LOADI': 1,  # ACC = immediate value
    'LOAD':  2,  # ACC = RAM[addr]
    'STORE': 3,  # RAM[addr] = ACC
    'ADD':   4,  # ACC = ACC + RAM[addr]; sets Z/N/V
    'SUB':   5,  # ACC = ACC - RAM[addr]; sets Z/N/V
    'JUMP':  6,  # PC = addr
    'JZ':    7,  # if ACC == 0: PC = addr
    'JNZ':   8,  # if ACC != 0: PC = addr
    'HALT':  9,  # stop execution
    'JLT':   10,  # if N XOR V (signed less-than from the last ADD/SUB/CMP; after
                  # CMP addr this means ACC < RAM[addr]): PC = addr
    'JOV':   11,  # if V (signed overflow from the last ADD/SUB/CMP): PC = addr
    'CMP':   12,  # ACC - RAM[addr], sets Z/N/V only — ACC is left unchanged
}

MNEMONICS = {v: k for k, v in OPCODES.items()}


def assemble(source_lines):
    """Two-pass assembler: resolves labels, then encodes each instruction
    into a single 16-bit int: (opcode << 12) | operand."""
    labels = {}
    cleaned = []

    # Pass 1: strip comments/blank lines, record label positions
    for line in source_lines:
        line = line.split(';')[0].strip()
        if not line:
            continue
        if line.endswith(':'):
            labels[line[:-1]] = len(cleaned)
        else:
            cleaned.append(line)

    # Pass 2: encode
    program = []
    for line in cleaned:
        parts = line.replace(',', ' ').split()
        mnemonic = parts[0].upper()
        if mnemonic not in OPCODES:
            raise ValueError(f"Unknown instruction: {mnemonic}")
        opcode = OPCODES[mnemonic]
        operand = 0
        if len(parts) > 1:
            arg = parts[1]
            operand = labels[arg] if arg in labels else int(arg)
        program.append((opcode << 12) | (operand & 0xFFF))

    return program
