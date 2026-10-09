"""
demo.py — the full pipeline in action.

Assembles a small program (sum the numbers 1 to 10), runs it on our
NAND-built CPU cycle by cycle, prints a live trace, and generates an
HTML gate-cost visualizer report.

Run: python3 demo.py
"""

import gates
from assembler import assemble
from cpu import CPU
from visualizer import generate_html_report

PROGRAM_SOURCE = """
; sum the numbers 1..10 using a simple counting loop
; RAM[0] = counter (10 -> 0), RAM[1] = running sum, RAM[2] = constant 1

LOADI 10
STORE 0
LOADI 0
STORE 1
LOADI 1
STORE 2
LOOP:
LOAD 1
ADD 0
STORE 1
LOAD 0
SUB 2
STORE 0
JNZ LOOP
LOAD 1
HALT
"""


def main():
    gates.reset_gate_count()

    program = assemble(PROGRAM_SOURCE.strip().split('\n'))
    print(f"Assembled {len(program)} instructions.\n")

    cpu = CPU(program, trace=True)
    result = cpu.run()

    print()
    print(f"Program finished in {cpu.cycle} cycles.")
    print(f"Result (sum of 1..10) = {result}")
    print(f"Total NAND gates fired: {gates.GATE_COUNT}")
    print(f"Average NAND gates per cycle: {gates.GATE_COUNT / cpu.cycle:.1f}")

    out_path = generate_html_report(cpu, result, "trace_report.html")
    print(f"\nVisual report written to {out_path}")


if __name__ == "__main__":
    main()
