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
| 4 | ADD addr | ACC += RAM[addr]; sets Z/N/V |
| 5 | SUB addr | ACC -= RAM[addr]; sets Z/N/V |
| 6 | JUMP addr | PC = addr |
| 7 | JZ addr | if ACC == 0: PC = addr |
| 8 | JNZ addr | if ACC != 0: PC = addr |
| 9 | HALT | stop |
| 10 | JLT addr | if N XOR V (signed less-than from the last ADD/SUB/CMP; after `CMP addr` this means ACC < RAM[addr]): PC = addr |
| 11 | JOV addr | if V (signed overflow from the last ADD/SUB/CMP): PC = addr |
| 12 | CMP addr | ACC - RAM[addr], sets Z/N/V only — ACC is left unchanged |

Each instruction is packed into 16 bits: `[4-bit opcode][12-bit operand]`.

### Status flags

ADD, SUB, and CMP update a 3-bit status register, built entirely from the
same NAND-derived gates as everything else:

- **Z** (zero) — `is_zero16(result)`
- **N** (negative) — the result's sign bit (bit 15), tapped directly
- **V** (signed overflow) — two's-complement overflow:
  - ADD: `V = (a15 == b15) AND (sum15 != a15)`
  - SUB: `V = (a15 != b15) AND (diff15 != a15)`

`JLT` (signed less-than, `N XOR V`) and `JOV` (overflow) branch on that
register, so comparisons and division loops run as real hardware-style
conditional branches instead of precomputed constants. `CMP` is just `SUB`
with the ACC write suppressed — the classic "compare" trick.

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
31,712 NAND gates total (all bottom-up, traceable to `Nand()`; this rose
from the project's original ~30,000 once ADD/SUB started computing the
Z/N/V status flags on every cycle, not just the result).
