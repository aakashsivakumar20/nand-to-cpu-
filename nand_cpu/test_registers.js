"use strict";
/*
 * test_registers.js — sanity checks for the NAND-built memory hierarchy
 * in interactive.html's JS port: SR latch -> gated D latch -> master-
 * slave DFF -> Bit -> GateRegister -> RAM8.
 *
 * This does NOT maintain a second copy of the logic: it extracts the
 * real <script> block out of interactive.html and runs it in a sandboxed
 * VM context (with a minimal DOM stub so the page's top-level
 * `document.getElementById(...)` calls don't throw), so these tests
 * exercise the exact code the browser would run.
 *
 * Run: node test_registers.js
 */

const fs = require("fs");
const path = require("path");
const vm = require("vm");

function loadPageScript() {
  const html = fs.readFileSync(path.join(__dirname, "interactive.html"), "utf8");
  const m = html.match(/<script>\r?\n([\s\S]*?)\r?\n<\/script>/);
  if (!m) throw new Error("could not find <script> block in interactive.html");
  const js = m[1];

  function makeEl() {
    return {
      style: {}, className: "", textContent: "", innerHTML: "", value: "",
      dataset: {}, addEventListener() {},
    };
  }
  const sandbox = {
    document: { getElementById: () => makeEl(), querySelectorAll: () => [] },
    console,
  };
  const context = vm.createContext(sandbox);

  // `const`/`let`/`class` top-level bindings do NOT become properties of
  // the vm context object the way `var`/function declarations do — so
  // append an IIFE, run as PART OF THE SAME SCRIPT (same lexical scope,
  // same source text), that closes over everything we need and exports
  // it onto globalThis. This tests the real extracted page script, not
  // a reimplementation.
  const exportNames = [
    "srLatch", "dLatch", "DFF", "Bit", "GateRegister", "RAM8",
    "intToBits", "bitsToInt", "assemble", "CPU", "EXAMPLES", "genDivide",
  ];
  const exporter = `
;(function(){
  globalThis.__T = { ${exportNames.join(", ")}, getGateCount: function(){ return GATE_COUNT; }, resetGateCount: resetGateCount };
})();
`;
  vm.runInContext(js + exporter, context, { filename: "interactive.html (extracted script)" });
  return context.__T;
}

const page = loadPageScript();

let passCount = 0, failCount = 0;
function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  console.log(`[${ok ? "PASS" : "FAIL"}] ${label}: got ${JSON.stringify(actual)}, expected ${JSON.stringify(expected)}`);
  if (ok) passCount++; else failCount++;
}

// ---- SR latch: set / reset / hold ----
{
  let [q, qn] = [0, 1];
  [q, qn] = page.srLatch(1, 0, q, qn);
  check("SR latch set -> [q,qn]", [q, qn], [1, 0]);
  [q, qn] = page.srLatch(0, 0, q, qn);
  check("SR latch hold after set -> [q,qn]", [q, qn], [1, 0]);
  [q, qn] = page.srLatch(0, 1, q, qn);
  check("SR latch reset -> [q,qn]", [q, qn], [0, 1]);
  [q, qn] = page.srLatch(0, 0, q, qn);
  check("SR latch hold after reset -> [q,qn]", [q, qn], [0, 1]);
}

// ---- SR latch: documented forbidden input ----
{
  const [q, qn] = page.srLatch(1, 1, 0, 1);
  check("SR latch forbidden input -> [q,qn]", [q, qn], [1, 1]);
}

// ---- gated D latch: transparent / hold ----
{
  let [q, qn] = [0, 1];
  [q, qn] = page.dLatch(1, 1, q, qn);
  check("D latch transparent d=1", q, 1);
  [q, qn] = page.dLatch(0, 1, q, qn);
  check("D latch transparent d=0", q, 0);
  [q, qn] = page.dLatch(1, 0, q, qn);
  check("D latch holds through d change", q, 0);
}

// ---- DFF: captures only on the clock edge ----
{
  const dff = new page.DFF();
  check("DFF initial q", dff.q, 0);
  dff.phaseLow(1);
  check("DFF q unaffected by phaseLow alone", dff.q, 0);
  dff.phaseHigh();
  check("DFF q after the clock edge completes", dff.q, 1);
  check("DFF tick(0)", dff.tick(0), 0);
  check("DFF tick(1)", dff.tick(1), 1);
}

// ---- Bit: write and hold ----
{
  const bit = new page.Bit();
  check("Bit load=1 d=1", bit.tick(1, 1), 1);
  check("Bit load=0 holds", bit.tick(0, 0), 1);
  check("Bit load=1 d=0", bit.tick(1, 0), 0);
  check("Bit load=0 holds (0)", bit.tick(0, 1), 0);
}

// ---- GateRegister: write and hold ----
{
  const reg = new page.GateRegister();
  reg.tick(1, page.intToBits(0xBEEF));
  check("GateRegister load", page.bitsToInt(reg.bits) & 0xFFFF, 0xBEEF);
  reg.tick(0, page.intToBits(0));
  check("GateRegister hold", page.bitsToInt(reg.bits) & 0xFFFF, 0xBEEF);
  reg.tick(1, page.intToBits(0x1234));
  check("GateRegister second load", page.bitsToInt(reg.bits) & 0xFFFF, 0x1234);
}

// ---- RAM8 vs a plain behavioural model, random reads/writes ----
{
  // small xorshift PRNG so this is reproducible without depending on Math.random
  let seed = 42;
  function rnd() {
    seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5;
    seed = seed >>> 0;
    return seed / 4294967296;
  }

  const ram8 = new page.RAM8();
  const model = new Array(8).fill(0);
  let mismatch = null;

  for (let step = 0; step < 300; step++) {
    const addr = Math.floor(rnd() * 8);
    if (rnd() < 0.5) {
      const val = Math.floor(rnd() * 65536);
      ram8.write(page.intToBits(addr, 3), 1, page.intToBits(val));
      model[addr] = val & 0xFFFF;
    } else {
      ram8.write(page.intToBits(addr, 3), 0, page.intToBits(0));
    }
    for (let a = 0; a < 8; a++) {
      const got = page.bitsToInt(ram8.read(page.intToBits(a, 3))) & 0xFFFF;
      if (got !== model[a]) { mismatch = { step, a, got, expected: model[a] }; break; }
    }
    if (mismatch) break;
  }
  check("RAM8 matches behavioural model over 300 random ops x 8 reads", mismatch, null);
}

// ---- full CPU programs still halt correctly with the gate-built registers ----
{
  function runSource(src) {
    page.resetGateCount();
    const program = page.assemble(src.trim().split("\n"));
    const cpu = new page.CPU(program);
    const result = cpu.run(20000);
    return { result, cycles: cpu.cycle, gates: page.getGateCount(), halted: cpu.halted };
  }
  check("JS sum 1..10 still correct", runSource(page.EXAMPLES.sum), { result: 55, cycles: 78, gates: 143152, halted: true });
  check("JS 20/3 still correct", runSource(page.genDivide(20, 3).source).result, 6);
  check("JS 5/9 still correct", runSource(page.genDivide(5, 9).source).result, 0);
}

console.log(`\n${passCount} passed, ${failCount} failed.`);
if (failCount > 0) process.exit(1);
