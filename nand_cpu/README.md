# Building a Computer from a Single NAND Gate

A software-only simulation (no hardware, no HDL tools) that builds a small
working computer, layer by layer, starting from one primitive: `Nand()`.

```
NAND  →  gates  →  arithmetic (ALU)  →  memory  →  CPU  →  running program
```

## Files

| File | Layer | What it does |
|---|---|---|
| `gates.py` | 1. Combinational Logic | NAND → NOT, AND, OR, XOR, MUX, DMUX (+16-bit versions) |
| `arithmetic.py` | 2. Boolean Arithmetic | Half/Full adder → 16-bit adder → subtract → zero-check |
| `memory.py` | 3. Sequential Logic | Register, RAM, Program Counter |
| `assembler.py` | 4. CPU (instruction set) | Our own 10-instruction ISA + two-pass assembler |
| `cpu.py` | 4. CPU (execution) | Fetch–decode–execute loop, logs gate cost per cycle |
| `visualizer.py` | Extra | Turns the execution log into an HTML report |
| `demo.py` | — | Runs the "sum 1 to 10" program end-to-end |
| `test_gates.py` | — | Sanity-checks every layer against known truth tables |

## How to run

```bash
python3 test_gates.py   # confirm every layer is correct
python3 demo.py         # run the full CPU demo + generate trace_report.html
```

Open `trace_report.html` in a browser afterward to see the cycle-by-cycle
trace and the gate-cost bar chart.

## The instruction set (our own design)

| Opcode | Mnemonic | Meaning |
|---|---|---|
| 0 | NOP | do nothing |
| 1 | LOADI n | ACC = n |
| 2 | LOAD addr | ACC = RAM[addr] |
| 3 | STORE addr | RAM[addr] = ACC |
| 4 | ADD addr | ACC += RAM[addr] |
| 5 | SUB addr | ACC -= RAM[addr] |
| 6 | JUMP addr | PC = addr |
| 7 | JZ addr | if ACC == 0: PC = addr |
| 8 | JNZ addr | if ACC != 0: PC = addr |
| 9 | HALT | stop |

Each instruction is packed into 16 bits: `[4-bit opcode][12-bit operand]`.

## What "novel" means here

The base idea (building a CPU from gates) exists in the broader nand2tetris
course sequence. What's original in this project:

1. **A self-designed instruction set**, smaller than the standard course ISA
2. **A live gate-cost visualizer** — showing exactly how many NAND gates
   each instruction burns, not just the final answer
3. **An accumulator-style CPU architecture** chosen and justified independently

## Demo result

Running `demo.py` assembles and executes a small program that sums the
numbers 1 through 10 using a counting loop — no manual input after
`cpu.run()` is called. Expected output: `55`, in 78 clock cycles, using
~30,000 NAND gates total (all bottom-up, traceable to `Nand()`).
