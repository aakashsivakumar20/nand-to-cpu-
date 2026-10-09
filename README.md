# Building a Computer from a Single NAND Gate

A software-only simulation — no hardware, no HDL tools — that builds a small working
computer from one primitive, `Nand()`, straight up through gates, arithmetic, real
NAND-built flip-flop registers, a 13-instruction CPU with hardware-style status flags,
and a gate-level signal-path animation, in parallel Python and JavaScript
implementations that are checked against each other on every run.

```
NAND → gates → arithmetic (ALU) → registers (latches/flip-flops) → CPU (ISA + flags) → running programs
```

## Try it

Open **[`index.html`](index.html)** in any browser — it's the whole JS port in one
file, runs 100% client-side, and is this repo's GitHub Pages entry point (served from
the `main` branch root). Type assembly directly, use one of the natural-language
prompts ("sum the numbers from 1 to 5", "divide 20 by 3"), or open the **Signal Path**
panel to step through a 16-bit ADD one NAND gate at a time.

## Layers

| File | Layer | What it does |
|---|---|---|
| `nand_cpu/gates.py` | 1. Combinational logic | NAND → NOT, AND, OR, XOR, MUX, DMUX (+16-bit versions) |
| `nand_cpu/arithmetic.py` | 2. Boolean arithmetic | Half/full adder → 16-bit adder → subtract → zero-check → Z/N/V flags |
| `nand_cpu/memory.py` | 3. Sequential logic | Register, RAM, ProgramCounter — a **behavioural model** (see below) |
| `nand_cpu/registers.py` | 3b. Sequential logic, gate-built | SR latch → gated D latch → master-slave DFF → Bit → GateRegister → RAM8 |
| `nand_cpu/assembler.py` | 4. Instruction set | Our own 13-opcode ISA + two-pass assembler |
| `nand_cpu/cpu.py` | 4. CPU execution | Fetch–decode–execute loop, logs gate cost + flags per cycle |
| `nand_cpu/visualizer.py` | Extra | Turns an execution log into a standalone HTML trace report |
| `nand_cpu/demo.py` | — | Runs the "sum 1 to 10" program end-to-end |
| `index.html` | — | The full JS port: gates → CPU → assembler → NL front end → Signal Path panel |

`index.html` is a hand-maintained JS mirror of the Python package, not a transpile —
every demo below is checked to give identical results, cycles, and gate counts in
both.

## How to run (Windows PowerShell)

```powershell
cd nand_cpu
python test_gates.py        # gates, arithmetic, CPU, ISA, flags, cost table — 62 checks
python test_registers.py    # SR latch, D latch, DFF, GateRegister, RAM8 — 2426 checks
node test_registers.js      # same register hierarchy, against the real index.html script
python demo.py               # runs "sum 1..10", writes trace_report.html
```

Open `index.html` (repo root) directly in a browser for the interactive version —
no build step, no server.

## The instruction set (our own design)

Accumulator machine: one working register (ACC), everything else in RAM. Each
instruction is packed into 16 bits: `[4-bit opcode][12-bit operand]` — so `LOADI`'s
immediate and every address are limited to 0–4095.

| Opcode | Mnemonic | Meaning |
|---|---|---|
| 0 | `NOP` | do nothing |
| 1 | `LOADI n` | ACC = n |
| 2 | `LOAD addr` | ACC = RAM[addr] |
| 3 | `STORE addr` | RAM[addr] = ACC |
| 4 | `ADD addr` | ACC += RAM[addr]; sets Z/N/V |
| 5 | `SUB addr` | ACC -= RAM[addr]; sets Z/N/V |
| 6 | `JUMP addr` | PC = addr |
| 7 | `JZ addr` | if ACC == 0: PC = addr |
| 8 | `JNZ addr` | if ACC != 0: PC = addr |
| 9 | `HALT` | stop execution |
| 10 | `JLT addr` | if N XOR V (signed less-than from the last ADD/SUB/CMP; after `CMP addr` this means ACC < RAM[addr]): PC = addr |
| 11 | `JOV addr` | if V (signed overflow from the last ADD/SUB/CMP): PC = addr |
| 12 | `CMP addr` | ACC - RAM[addr], sets Z/N/V only — ACC is left unchanged |

### Status flags

ADD, SUB, and CMP update a 3-bit status register, built entirely from the same
NAND-derived gates as everything else — **not** on every instruction (LOAD/STORE/etc.
leave it untouched, like real hardware):

- **Z** (zero) — `is_zero16(result)`
- **N** (negative) — the result's sign bit (bit 15), tapped directly, no gate needed
- **V** (signed overflow) — two's-complement overflow, built from `Xor`/`And`/`Not`:
  - ADD: `V = (a15 == b15) AND (sum15 != a15)`
  - SUB: `V = (a15 != b15) AND (diff15 != a15)`

`JLT` (`N XOR V`) and `JOV` branch on that register — comparisons and the
natural-language division generator run as real conditional branches on real flags,
not precomputed constants. `CMP` is `SUB` with the ACC write suppressed.

## Memory: behavioural model vs. gate-built

`memory.py`'s `Register`/`RAM` are a **behavioural model** — `self.bits = list(...)`
on load, Python's own assignment standing in for "a register remembers a value". The
CPU's 256-word program/data RAM uses this; gate-building all 256 words would cost
millions of simulated NAND gates per cycle for no behavioural difference.

`registers.py` builds memory the way real hardware does, bottom-up, from nothing but
`Nand()`:

- **SR latch** — the textbook 2-gate active-LOW circuit, taken directly:
  `q = NAND(s_bar, qn)`, `qn = NAND(r_bar, q)`. No input inversion — callers that
  need active-low signals (like the D latch below) build them from ordinary NANDs.
- **Gated D latch** — the textbook 4-NAND circuit, taken directly: `a = NAND(d, en)`,
  `b = NAND(a, en)`, then `q = NAND(a, qn)`, `qn = NAND(b, q)` — the last two *are*
  the SR latch core above, fed `s_bar=a, r_bar=b`.
- **Master-slave D flip-flop** — two gated D latches (a master, transparent while the
  clock is low; a slave, transparent while it's high) plus one inverter deriving the
  master's enable from the clock. Captures only on the clock edge, not for however
  long D happens to be high.
- A 1-bit **`Bit`** cell with a load input, a 16-bit **`GateRegister`** built from 16
  `Bit`s, and **`RAM8`**, an 8-word RAM built from 8 `GateRegister`s behind a 3-bit
  DMux/Mux address decoder.

The CPU's ACC, program counter, and instruction register (IR) are real
`GateRegister`s — **`RAM8` is the gate-built proof** that the construction matches
the behavioural model exactly (checked against it on hundreds of random reads/writes
in `test_registers.py`/`.js`), not something wired into the CPU itself.

A feedback loop (the SR latch's cross-coupled pair) has no single-pass evaluation
order in software — finding where it settles means re-evaluating the same two gates
until the values stop changing. That's a software artifact, not a hardware one: real
latches are still just N physical gates firing once per clock phase. So the settle
loop uses an uncounted NAND, and `gates.count_physical(n)` attributes the real gate
count exactly once per call, independent of how many iterations settling took
(documented in `gates.py` and mirrored in `index.html`). The same rule applies to the
flip-flop's master latch: the clock transitioning closes it, but that's not a second
physical evaluation of the same 4 gates, so `phase_high()` doesn't re-run it — a
master-slave DFF spends exactly 2 latches + 1 inverter per tick, not 2 latches plus
one evaluated twice.

## Measured gate costs

Every number below came out of a real run — `test_gates.py`'s
`measure_instruction_costs()` probes each instruction independently, and
`test_per_instruction_cost_table_matches_real_programs()` checks that table against
the four programs below's own traces, instruction by instruction. None are
hand-derived or estimated.

**Per instruction** (fixed per opcode — this simulation has no short-circuiting, so
every instruction costs exactly the same gates every time regardless of operand
values; only branches have a taken/not-taken split, and "taken" always includes the
instruction-register load and the PC write, i.e. fetch (272) + a load-path PC write
(272) is baked into every taken cost below):

| Instruction | Gates | Why |
|---|---|---|
| NOP / STORE | 848 | fetch (IR load, 272) + PC increment (16-bit add16, 304 + GateRegister write, 272) |
| LOADI / LOAD | 1,120 | 848 + ACC write (272) |
| ADD | 1,488 | 848 + ACC write (272) + ALU: add16 (304) + Z/V flags (64) |
| SUB | 1,807 | 848 + ACC write (272) + ALU: negate+add (624) + Z/V flags (63) |
| CMP | 1,535 | 848 + ALU: negate+add (624) + Z/V flags (63) — **no** ACC write |
| JUMP | 544 | fetch (272) + PC load, no increment (272) — always, no condition logic |
| JLT | 550 (taken) / 854 (not taken) | the N XOR V gate (6) always fires; the 304-gate PC increment only fires when not taken |
| JZ / JNZ | 593 (taken) / 897 (not taken) | `is_zero16` (49) always fires |
| JOV | 544 (taken) / 848 (not taken) | reading V is a direct tap |
| HALT | 272 | fetch only — no PC tick, no ACC write |

**Registers** (`registers.py`/`test_registers.py`):

| Component | Gates |
|---|---|
| 1 SR latch call | 2 |
| 1 gated D latch call | 4 |
| 1 master-slave DFF tick | 9 |
| 1 Bit (1-bit cell) tick | 17 |
| 1 16-bit GateRegister tick | 272 |
| 1 RAM8 write | 2,227 |
| 1 RAM8 read | 1,059 |

**Demo totals** (Python == JS, exactly, on every run):

| Program | Result | Cycles | Gates |
|---|---|---|---|
| Sum 1..10 | 55 | 78 | 85,840 |
| Sum 1..300 (wraps, V flagged) | -20386 | 3,010 | 3,393,568 |
| 20 / 3 | 6 remainder 2 | 67 | 73,453 |
| 5 / 9 | 0 remainder 5 | 13 | 12,469 |

Sum 1..300 runs in well under a second in Node (14–49ms measured) — the gate-built
registers don't make the simulation noticeably slower.

## The Signal Path panel

`index.html`'s "Signal Path" panel visualizes one 16-bit ADD: step or Play through
the 16 full-adder cells (bit 0 → bit 15, the order the carry actually ripples),
watch the carry flow between cells, and click any cell to expand it into the 19
individual NAND gates that computed it — in the exact order they fired, with their
live 0/1 values. It's driven by instrumenting the real `Nand()`/`add16Flags()` the
CPU's ADD opcode calls (an optional trace recorder, not a second implementation), and
it includes a live self-check against the CPU: the panel's sum, flags, and gate count
must equal — and are asserted to equal, for several values including the 32767+1
overflow edge case — what running the same ADD on the actual CPU reports.

## Limitations

- **256-word RAM is a behavioural model**, not gate-built (see above); `RAM8` is the
  gate-built proof, at a scale that stays simulate-able, not the CPU's real memory.
- **12-bit operands.** `LOADI`'s immediate and every address are limited to 0–4095 —
  larger constants (the Signal Path panel's self-check, the JOV test) have to be
  built on-CPU via repeated doubling.
- **No multiply or divide instruction.** Both are assembled loops (repeated addition /
  repeated subtraction with a real `CMP`/`JLT` comparison), not single opcodes.
- **16-bit signed wraparound is real, not hidden.** Values outside
  [-32768, 32767] wrap, exactly like real two's-complement hardware; the V flag and
  the page's amber warning exist specifically to surface that instead of masking it.
- **This simulation has no gate propagation delay.** Feedback circuits (the SR latch)
  are settled by iterating to a fixed point rather than a physical race, which is why
  the documented forbidden input (`s_bar = r_bar = 0`, active-low) resolves
  deterministically here instead of being genuinely undefined.

## What's original here

The base idea — building a CPU from NAND gates — is the nand2tetris course sequence's;
this project is a from-scratch software simulation built independently in that
tradition, not a port of its HDL or test suite. Original to this project:

1. **A self-designed 13-opcode instruction set** with hardware-style Z/N/V status
   flags and signed-overflow/less-than branches (`JOV`/`JLT`), smaller than nand2tetris's.
2. **A live gate-cost visualizer and per-instruction cost table** — every number
   measured from an actual run, not estimated.
3. **A full NAND → latch → flip-flop → register → RAM8 hierarchy** built and tested
   independently of the CPU's behavioural RAM, with an explicit gate-counting rule for
   feedback circuits.
4. **A gate-level Signal Path animation** driven by instrumenting the production gate
   functions, with an automated equivalence check against the CPU.
5. **Parallel Python and JS implementations**, cross-checked against each other on
   every demo program as part of the test suite, not just visually similar.

## License

MIT — see [LICENSE](LICENSE).
