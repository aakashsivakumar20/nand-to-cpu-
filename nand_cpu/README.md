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
| `memory.py` | 3. Sequential Logic | Register, RAM, Program Counter — a **behavioural model** (see below) |
| `registers.py` | 3b. Sequential Logic, gate-built | SR latch → gated D latch → master-slave DFF → Bit → GateRegister → RAM8 |
| `assembler.py` | 4. CPU (instruction set) | Our own 13-instruction ISA + two-pass assembler |
| `cpu.py` | 4. CPU (execution) | Fetch–decode–execute loop, logs gate cost + flags per cycle |
| `visualizer.py` | Extra | Turns the execution log into an HTML report |
| `demo.py` | — | Runs the "sum 1 to 10" program end-to-end |
| `test_gates.py` | — | Sanity-checks gates/arithmetic/CPU/ISA against known truth tables |
| `test_registers.py` | — | Sanity-checks the gate-built register hierarchy and RAM8 |

### Behavioural model vs. gate-built memory

`memory.py`'s `Register`/`RAM` are a **behavioural model**: `self.bits =
list(...)` on load, i.e. Python's own assignment stands in for "a register
remembers a value". That's what the CPU's 256-word program/data RAM uses —
building all 256 words from real NAND-gate flip-flops would cost millions
of simulated gates per cycle for no behavioural difference.

`registers.py` builds memory the way real hardware does, bottom-up, from
nothing but `Nand()`: a cross-coupled NAND pair (SR latch) → a gated D
latch → a master-slave D flip-flop (captures only on the clock edge) → a
1-bit `Bit` cell with a load input → a 16-bit `GateRegister` → `RAM8`, an
8-word RAM built from 8 `GateRegister`s behind a 3-bit address decoder.
**`RAM8` is the gate-built proof** that this construction is a faithful
stand-in for the behavioural model — `test_registers.py` checks it against
that model on hundreds of random reads and writes. `RAM8` itself is not
wired into the CPU (only tested); the CPU's ACC, program counter, and
instruction register, however, are real `GateRegister`s.

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
