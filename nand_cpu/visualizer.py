"""
visualizer.py — turns a CPU's execution log into a self-contained HTML
report: a summary strip, plus a per-cycle table with a bar showing how
many NAND gates fired on each instruction (the "gate-cost" analysis).
"""


def generate_html_report(cpu, result, out_path):
    trace = cpu.log
    total_gates = sum(t['gates_used'] for t in trace)
    cycles = cpu.cycle
    max_gates = max((t['gates_used'] for t in trace), default=1) or 1
    overflowed = any(t['v'] for t in trace)

    rows = []
    for t in trace:
        bar_width = int((t['gates_used'] / max_gates) * 200)
        rows.append(f"""
        <tr>
          <td>{t['cycle']}</td>
          <td>{t['pc']}</td>
          <td>{t['mnemonic']} {t['operand']}</td>
          <td>{t['acc_before']} &rarr; {t['acc_after']}</td>
          <td>Z={t['z']} N={t['n']} V={t['v']}</td>
          <td>{t['gates_used']}<div class="bar" style="width:{bar_width}px"></div></td>
        </tr>""")

    overflow_banner = ("""
<div class="overflow-warning">&#9888; Overflow: result wrapped (16-bit signed)</div>"""
                        if overflowed else "")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>NAND-to-CPU Execution Trace</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; background:#0f1117; color:#e6e6e6; padding:32px; }}
  h1 {{ color:#7dd3fc; margin-bottom:4px; }}
  .subtitle {{ color:#9aa0ab; margin-bottom:24px; }}
  .summary {{ background:#1a1d27; padding:18px 24px; border-radius:10px; margin-bottom:24px; display:flex; gap:36px; }}
  .stat b {{ color:#7dd3fc; font-size:24px; display:block; }}
  .stat span {{ color:#9aa0ab; font-size:13px; }}
  table {{ border-collapse: collapse; width:100%; background:#151822; border-radius:8px; overflow:hidden; }}
  th, td {{ padding:9px 14px; border-bottom:1px solid #262a38; text-align:left; font-size:13px; }}
  th {{ color:#7dd3fc; background:#1a1d27; position:sticky; top:0; }}
  .bar {{ height:6px; background:linear-gradient(90deg,#7dd3fc,#38bdf8); border-radius:3px; margin-top:5px; }}
  tr:hover {{ background:#1c2030; }}
  .overflow-warning {{
    background: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.45);
    color: #fbbf24; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px; font-weight: 600;
  }}
</style>
</head>
<body>
<h1>NAND-to-CPU Execution Trace</h1>
<div class="subtitle">Every value here is the product of primitive NAND gates only.</div>
{overflow_banner}
<div class="summary">
  <div class="stat"><b>{result}</b><span>Result</span></div>
  <div class="stat"><b>{cycles}</b><span>Cycles executed</span></div>
  <div class="stat"><b>{total_gates}</b><span>Total NAND gates fired</span></div>
  <div class="stat"><b>{total_gates / max(cycles,1):.1f}</b><span>Avg gates / cycle</span></div>
</div>
<table>
<tr><th>Cycle</th><th>PC</th><th>Instruction</th><th>ACC</th><th>Flags</th><th>Gates used this cycle</th></tr>
{''.join(rows)}
</table>
</body>
</html>"""

    with open(out_path, 'w') as f:
        f.write(html)
    return out_path
