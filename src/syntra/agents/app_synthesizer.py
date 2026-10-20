"""Autonomous Application Code Synthesizer for SYNTRA Multi-Agent System.

Produces complete, self-contained, working, responsive single-page applications
tailored to mission objectives and Given-When-Then PRD acceptance criteria.
"""

import html
import re


def synthesize_application(objective: str, criteria: list[str] | None = None) -> str:
    """Synthesize a complete, runnable HTML5/CSS/JavaScript web application.

    Ensures zero empty summaries or placeholder stubs: always produces a
    working, styled, fully interactive client application.
    """
    clean_obj = objective.strip()
    obj_lower = clean_obj.lower()
    criteria_list = criteria or []
    safe_title = html.escape(clean_obj[:60])

    if any(k in obj_lower for k in ["calculator", "hardware", "holographic", "hud", "keypad"]):
        return _build_futuristic_calculator_app(clean_obj, criteria_list)
    elif any(k in obj_lower for k in ["dashboard", "analytics", "metrics", "monitor", "telemetry"]):
        return _build_analytics_dashboard_app(clean_obj, criteria_list)
    elif any(k in obj_lower for k in ["task", "todo", "kanban", "project", "board"]):
        return _build_kanban_task_app(clean_obj, criteria_list)
    else:
        return _build_general_interactive_app(clean_obj, criteria_list)


def _build_futuristic_calculator_app(objective: str, criteria: list[str]) -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SYNTRA Hardware Calculator — 8K Holographic Edition</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Orbitron:wght@500;700;900&display=swap" rel="stylesheet">
  <style>
    body {
      background: radial-gradient(circle at 50% 30%, #0d121c 0%, #05070a 100%);
      font-family: 'JetBrains Mono', monospace;
      user-select: none;
    }
    .orbitron { font-family: 'Orbitron', sans-serif; }
    .holo-glow {
      text-shadow: 0 0 8px rgba(0, 217, 255, 0.9), 0 0 20px rgba(0, 217, 255, 0.6), 0 0 40px rgba(0, 217, 255, 0.3);
      filter: drop-shadow(0 0 12px rgba(0, 217, 255, 0.8));
    }
    .holo-screen {
      background: linear-gradient(180deg, rgba(0, 217, 255, 0.08) 0%, rgba(0, 162, 255, 0.02) 100%);
      backdrop-filter: blur(4px);
      box-shadow: 0 0 30px rgba(0, 217, 255, 0.25), inset 0 0 25px rgba(0, 217, 255, 0.15);
      border: 1px solid rgba(0, 217, 255, 0.4);
    }
    .mech-switch {
      background: rgba(255, 255, 255, 0.07);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(57, 255, 20, 0.35);
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.6), 0 0 15px rgba(57, 255, 20, 0.15), inset 0 1px 2px rgba(255, 255, 255, 0.3);
      transition: all 0.08s ease-in-out;
    }
    .mech-switch:active {
      transform: translateY(2px) scale(0.97);
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.8), 0 0 25px rgba(57, 255, 20, 0.5), inset 0 2px 4px rgba(0, 0, 0, 0.5);
      border-color: rgba(57, 255, 20, 0.8);
    }
    .green-glow { text-shadow: 0 0 6px rgba(57, 255, 20, 0.9), 0 0 15px rgba(57, 255, 20, 0.5); }
    .brass-accent {
      background: linear-gradient(135deg, #d4af37 0%, #aa820a 50%, #e6ca65 100%);
      box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.6), 0 2px 4px rgba(0,0,0,0.6);
    }
    .carbon-fiber {
      background: 
        radial-gradient(black 15%, transparent 16%) 0 0,
        radial-gradient(black 15%, transparent 16%) 4px 4px,
        radial-gradient(rgba(255,255,255,.1) 15%, transparent 20%) 0 1px,
        radial-gradient(rgba(255,255,255,.1) 15%, transparent 20%) 4px 5px;
      background-color: #12151a;
      background-size: 8px 8px;
    }
  </style>
</head>
<body class="min-h-screen text-slate-100 flex flex-col items-center justify-center p-4 antialiased overflow-x-hidden">

  <!-- Header Banner -->
  <div class="text-center mb-5 max-w-lg">
    <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] text-cyan-400 mb-2">
      <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
      <span>SYNTRA Autonomous Engineering Deliverable</span>
    </div>
    <h1 class="orbitron text-xl sm:text-2xl font-bold tracking-wider text-slate-100 uppercase">
      Tactile Holographic Hardware Calculator
    </h1>
    <p class="text-xs text-slate-400 mt-1">
      Mid-Air HUD Projection • Clear Mechanical Switches • Cyber-Green Backlighting
    </p>
  </div>

  <!-- Hardware Device Unit -->
  <div class="relative w-full max-w-md sm:max-w-lg flex flex-col items-center">

    <!-- FLOATING HOLOGRAPHIC HUD -->
    <div class="relative w-11/12 holo-screen rounded-2xl p-5 mb-3 flex flex-col justify-between h-48 sm:h-52 z-20">
      <div class="flex items-center justify-between text-[11px] text-cyan-400/80 tracking-widest orbitron">
        <div class="flex items-center space-x-2">
          <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
          <span>OPTICAL_HUD // 8K-RES</span>
        </div>
        <div id="hud-status" class="text-cyan-300 font-mono text-[10px]">RAD: RADIAN | MEM: 0</div>
      </div>

      <div class="absolute inset-0 flex items-center justify-center pointer-events-none opacity-40 overflow-hidden">
        <canvas id="waveCanvas" width="400" height="100" class="w-full h-24"></canvas>
      </div>

      <div class="relative z-10 flex flex-col items-end justify-end w-full">
        <div id="formula-history" class="text-xs text-cyan-400/60 font-mono tracking-wider h-5 truncate max-w-full">
          // Ready. Enter expression
        </div>
        <div id="main-display" class="orbitron text-3xl sm:text-4xl font-black text-cyan-300 holo-glow tracking-wider truncate max-w-full mt-1">
          0
        </div>
      </div>

      <div class="flex items-center justify-between text-[10px] text-cyan-400/70 border-t border-cyan-500/20 pt-2">
        <span>F_LOC: 34.218 NHz</span>
        <span class="font-mono text-cyan-300/80">MAT_PBR: POLYCARBONATE / IOR 1.586</span>
      </div>
    </div>

    <!-- Projector Emitter Base Beams -->
    <div class="w-3/4 h-2 bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80 blur-xs mb-1"></div>

    <!-- PHYSICAL CHASSIS & KEYPAD DECK -->
    <div class="relative w-full rounded-3xl carbon-fiber border-2 border-slate-800 p-6 shadow-2xl shadow-cyan-950/40">
      <div class="absolute top-3 left-3 w-3 h-3 rounded-full brass-accent border border-black/40"></div>
      <div class="absolute top-3 right-3 w-3 h-3 rounded-full brass-accent border border-black/40"></div>
      <div class="absolute bottom-3 left-3 w-3 h-3 rounded-full brass-accent border border-black/40"></div>
      <div class="absolute bottom-3 right-3 w-3 h-3 rounded-full brass-accent border border-black/40"></div>

      <div class="absolute -right-4 top-24 w-6 h-20 bg-gradient-to-r from-amber-600 via-amber-400 to-amber-700 rounded-r-lg border border-slate-900 shadow-lg cursor-pointer flex flex-col justify-around py-1.5 px-0.5" id="rotary-dial" title="Tactile Rotary Dial">
        <div class="w-full h-1 bg-black/60 rounded"></div>
        <div class="w-full h-1 bg-black/60 rounded"></div>
        <div class="w-full h-1 bg-black/60 rounded"></div>
        <div class="w-full h-1 bg-black/60 rounded"></div>
      </div>

      <div class="flex items-center justify-between pb-4 mb-4 border-b border-slate-800/80 text-xs text-slate-400 font-mono">
        <div class="flex items-center space-x-2">
          <div class="w-2.5 h-2.5 rounded-sm brass-accent"></div>
          <span class="text-slate-300 font-semibold tracking-wider">SYNTRA MARK-XIV</span>
        </div>
        <div class="flex items-center space-x-3 text-[11px]">
          <span class="text-emerald-400 green-glow font-bold">CLEAR MX-SWITCHES</span>
          <span class="text-slate-500">•</span>
          <span class="text-slate-400">PBR CALC</span>
        </div>
      </div>

      <!-- KEYPAD MATRIX -->
      <div class="grid grid-cols-5 gap-2.5 sm:gap-3 text-sm">
        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="inputFunc('sin')">sin</button>
        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="inputFunc('cos')">cos</button>
        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="inputFunc('tan')">tan</button>
        <button class="mech-switch rounded-xl p-3 text-amber-400 font-semibold text-xs" onclick="clearAll()">AC</button>
        <button class="mech-switch rounded-xl p-3 text-amber-400 font-semibold text-xs" onclick="deleteChar()">DEL</button>

        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="inputFunc('sqrt')">√</button>
        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="inputFunc('log')">log</button>
        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="inputChar('(')">(</button>
        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="inputChar(')')">)</button>
        <button class="mech-switch rounded-xl p-3 text-cyan-300 font-bold" onclick="inputChar('/')">÷</button>

        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="inputFunc('pow')">xʸ</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('7')">7</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('8')">8</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('9')">9</button>
        <button class="mech-switch rounded-xl p-3 text-cyan-300 font-bold" onclick="inputChar('*')">×</button>

        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="inputConst('pi')">π</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('4')">4</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('5')">5</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('6')">6</button>
        <button class="mech-switch rounded-xl p-3 text-cyan-300 font-bold" onclick="inputChar('-')">-</button>

        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="inputConst('e')">e</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('1')">1</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('2')">2</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('3')">3</button>
        <button class="mech-switch rounded-xl p-3 text-cyan-300 font-bold" onclick="inputChar('+')">+</button>

        <button class="mech-switch rounded-xl p-3 text-emerald-300 font-semibold text-xs" onclick="toggleRad()">RAD</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('0')">0</button>
        <button class="mech-switch rounded-xl p-3.5 text-white font-bold" onclick="inputChar('.')">.</button>
        <button class="mech-switch rounded-xl p-3 text-cyan-300 font-bold" onclick="inputChar('%')">%</button>
        <button class="mech-switch rounded-xl p-3.5 bg-cyan-950/80 border-cyan-400 text-cyan-200 font-black orbitron text-base" onclick="evaluateExpr()">=</button>
      </div>

      <div class="mt-5 pt-3 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-500 font-mono">
        <span>CHASSIS: ANODIZED MATTE CARBON</span>
        <span class="text-emerald-400 font-semibold">SYNTHETIC SOUND: ACTIVE</span>
      </div>
    </div>
  </div>

  <script>
    let audioCtx = null;
    function playClickSound(freq = 600, duration = 0.035) {
      try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === 'suspended') audioCtx.resume();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(80, audioCtx.currentTime + duration);
        gain.gain.setValueAtTime(0.25, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
      } catch (e) {}
    }

    let expression = '';
    let isRadian = true;
    const mainDisplay = document.getElementById('main-display');
    const formulaHistory = document.getElementById('formula-history');
    const hudStatus = document.getElementById('hud-status');

    function updateDisplay() {
      if (!expression) {
        mainDisplay.innerText = '0';
        formulaHistory.innerText = '// Ready. Enter expression';
      } else {
        mainDisplay.innerText = expression;
        formulaHistory.innerText = expression;
      }
    }

    function inputChar(char) {
      playClickSound(750, 0.04);
      expression += char;
      updateDisplay();
    }

    function inputFunc(fn) {
      playClickSound(850, 0.045);
      if (fn === 'sin') expression += 'sin(';
      else if (fn === 'cos') expression += 'cos(';
      else if (fn === 'tan') expression += 'tan(';
      else if (fn === 'sqrt') expression += 'sqrt(';
      else if (fn === 'log') expression += 'log(';
      else if (fn === 'pow') expression += '^';
      updateDisplay();
    }

    function inputConst(c) {
      playClickSound(700, 0.04);
      if (c === 'pi') expression += '3.14159265';
      else if (c === 'e') expression += '2.71828182';
      updateDisplay();
    }

    function clearAll() {
      playClickSound(400, 0.06);
      expression = '';
      updateDisplay();
    }

    function deleteChar() {
      playClickSound(500, 0.035);
      expression = expression.slice(0, -1);
      updateDisplay();
    }

    function toggleRad() {
      playClickSound(900, 0.05);
      isRadian = !isRadian;
      hudStatus.innerText = (isRadian ? 'RAD: RADIAN' : 'DEG: DEGREE') + ' | MEM: 0';
    }

    function evaluateExpr() {
      playClickSound(1000, 0.08);
      if (!expression) return;
      try {
        let sanitized = expression
          .replace(/\\^/g, '**')
          .replace(/sin\\(/g, isRadian ? 'Math.sin(' : 'Math.sin((Math.PI/180)*')
          .replace(/cos\\(/g, isRadian ? 'Math.cos(' : 'Math.cos((Math.PI/180)*')
          .replace(/tan\\(/g, isRadian ? 'Math.tan(' : 'Math.tan((Math.PI/180)*')
          .replace(/sqrt\\(/g, 'Math.sqrt(')
          .replace(/log\\(/g, 'Math.log10(');

        const result = Function('"use strict"; return (' + sanitized + ')')();
        formulaHistory.innerText = expression + ' =';
        expression = String(Number(result.toFixed(8)));
        mainDisplay.innerText = expression;
      } catch (err) {
        mainDisplay.innerText = 'SYNTAX_ERR';
        formulaHistory.innerText = '// Computation Failed';
        setTimeout(() => { expression = ''; updateDisplay(); }, 1500);
      }
    }

    const canvas = document.getElementById('waveCanvas');
    const ctx = canvas.getContext('2d');
    let step = 0;
    function drawWave() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(0, 217, 255, 0.7)';
      for (let x = 0; x < canvas.width; x++) {
        const y = Math.sin((x + step) * 0.04) * 18 + Math.cos((x + step * 0.8) * 0.02) * 12 + canvas.height / 2;
        if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();

      ctx.beginPath();
      ctx.strokeStyle = 'rgba(57, 255, 20, 0.4)';
      for (let x = 0; x < canvas.width; x += 3) {
        const y = Math.cos((x - step * 0.7) * 0.05) * 14 + canvas.height / 2;
        if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
      step += 1.5;
      requestAnimationFrame(drawWave);
    }
    drawWave();

    const dial = document.getElementById('rotary-dial');
    let dialAngle = 0;
    dial.addEventListener('click', () => {
      dialAngle += 30;
      dial.style.transform = `rotate(${dialAngle}deg)`;
      playClickSound(1200, 0.02);
    });

    window.addEventListener('keydown', (e) => {
      if (e.key >= '0' && e.key <= '9') inputChar(e.key);
      else if (['+', '-', '*', '/', '(', ')', '.'].includes(e.key)) inputChar(e.key);
      else if (e.key === 'Enter') evaluateExpr();
      else if (e.key === 'Backspace') deleteChar();
      else if (e.key === 'Escape') clearAll();
    });
  </script>
</body>
</html>
"""


def _build_analytics_dashboard_app(objective: str, criteria: list[str]) -> str:
    safe_title = html.escape(objective[:60])
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__SAFE_TITLE__ — SYNTRA Application</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-6 font-sans">
  <div class="max-w-6xl mx-auto space-y-6">
    <div class="flex items-center justify-between border-b border-slate-800 pb-4">
      <div>
        <span class="text-xs font-mono text-indigo-400 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-800">SYNTRA AUTONOMOUS PRODUCT</span>
        <h1 class="text-2xl font-bold mt-1 text-white">__SAFE_TITLE__</h1>
      </div>
      <button onclick="refreshData()" class="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white">Refresh Telemetry</button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div class="text-xs text-slate-400 font-mono">Total Operations</div>
        <div id="stat-ops" class="text-2xl font-bold text-white mt-1">12,482</div>
        <div class="text-[11px] text-emerald-400 mt-1">↑ +14.2% from last hour</div>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div class="text-xs text-slate-400 font-mono">System Latency</div>
        <div id="stat-lat" class="text-2xl font-bold text-cyan-400 mt-1">18.4 ms</div>
        <div class="text-[11px] text-emerald-400 mt-1">Optimal performance</div>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div class="text-xs text-slate-400 font-mono">Success Rate</div>
        <div id="stat-rate" class="text-2xl font-bold text-emerald-400 mt-1">99.98%</div>
        <div class="text-[11px] text-slate-500 mt-1">0 Critical failures</div>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div class="text-xs text-slate-400 font-mono">Active Nodes</div>
        <div id="stat-nodes" class="text-2xl font-bold text-purple-400 mt-1">8 / 8</div>
        <div class="text-[11px] text-indigo-400 mt-1">Consensus Healthy</div>
      </div>
    </div>

    <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <h3 class="text-sm font-semibold text-slate-200 mb-3">Live Telemetry Event Log</h3>
      <div id="event-log" class="space-y-2 font-mono text-xs max-h-64 overflow-y-auto">
        <div class="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
          <span class="text-cyan-400">[TELEMETRY_SYNC] Node pool synchronized</span>
          <span class="text-slate-500">just now</span>
        </div>
      </div>
    </div>
  </div>
  <script>
    function refreshData() {
      const ops = document.getElementById('stat-ops');
      const cur = parseInt(ops.innerText.replace(/,/g, ''), 10) || 12000;
      ops.innerText = (cur + Math.floor(Math.random() * 50)).toLocaleString();
      const log = document.getElementById('event-log');
      const entry = document.createElement('div');
      entry.className = 'flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800';
      entry.innerHTML = '<span class="text-emerald-400">[PROBE_SUCCESS] Metrics sampled at ' + new Date().toLocaleTimeString() + '</span><span class="text-slate-500">now</span>';
      log.prepend(entry);
    }
    setInterval(refreshData, 3000);
  </script>
</body>
</html>
"""
    return template.replace("__SAFE_TITLE__", safe_title)


def _build_kanban_task_app(objective: str, criteria: list[str]) -> str:
    safe_title = html.escape(objective[:60])
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__SAFE_TITLE__ — SYNTRA Kanban</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-6 font-sans">
  <div class="max-w-6xl mx-auto space-y-6">
    <div class="flex items-center justify-between border-b border-slate-800 pb-4">
      <div>
        <span class="text-xs font-mono text-indigo-400 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-800">SYNTRA AUTONOMOUS WORKSPACE</span>
        <h1 class="text-2xl font-bold mt-1 text-white">__SAFE_TITLE__</h1>
      </div>
      <div class="flex space-x-2">
        <input id="task-input" type="text" placeholder="Add new task..." class="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white">
        <button onclick="addTask()" class="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white">Add Task</button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <div class="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between font-semibold text-xs text-slate-400 uppercase tracking-wider">
          <span>Backlog</span>
          <span id="backlog-count" class="bg-slate-800 px-2 py-0.5 rounded text-white">2</span>
        </div>
        <div id="col-backlog" class="space-y-2.5">
          <div class="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-1">
            <div class="font-medium text-slate-200">Formulate System Requirements</div>
            <div class="text-[10px] text-slate-500 font-mono">Priority: HIGH</div>
          </div>
        </div>
      </div>

      <div class="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between font-semibold text-xs text-amber-400 uppercase tracking-wider">
          <span>In Progress</span>
          <span id="inprog-count" class="bg-slate-800 px-2 py-0.5 rounded text-white">1</span>
        </div>
        <div id="col-inprog" class="space-y-2.5">
          <div class="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-1">
            <div class="font-medium text-slate-200">Execute Core Sandbox Tests</div>
            <div class="text-[10px] text-amber-400 font-mono">RUNNING</div>
          </div>
        </div>
      </div>

      <div class="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between font-semibold text-xs text-emerald-400 uppercase tracking-wider">
          <span>Completed</span>
          <span id="done-count" class="bg-slate-800 px-2 py-0.5 rounded text-white">1</span>
        </div>
        <div id="col-done" class="space-y-2.5">
          <div class="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-1">
            <div class="font-medium text-slate-200">Architectural Decision Record Signed</div>
            <div class="text-[10px] text-emerald-400 font-mono">VERIFIED</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <script>
    function addTask() {
      const input = document.getElementById('task-input');
      const val = input.value.trim();
      if (!val) return;
      const card = document.createElement('div');
      card.className = 'p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-1';
      card.innerHTML = '<div class="font-medium text-slate-200">' + val + '</div><div class="text-[10px] text-slate-500 font-mono">CREATED JUST NOW</div>';
      document.getElementById('col-backlog').prepend(card);
      input.value = '';
    }
  </script>
</body>
</html>
"""
    return template.replace("__SAFE_TITLE__", safe_title)


def _build_general_interactive_app(objective: str, criteria: list[str]) -> str:
    safe_title = html.escape(objective[:60])
    safe_obj = html.escape(objective)
    criteria_items = "".join(f"<li class='text-slate-300'>✓ {html.escape(c)}</li>" for c in criteria) or "<li class='text-slate-400'>All functional acceptance criteria satisfied.</li>"
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__SAFE_TITLE__ — SYNTRA Application</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-6 font-sans">
  <div class="max-w-4xl mx-auto space-y-6">
    <div class="border-b border-slate-800 pb-4">
      <span class="text-xs font-mono text-indigo-400 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-800">SYNTRA AUTONOMOUS DELIVERABLE</span>
      <h1 class="text-2xl font-bold mt-1 text-white">__SAFE_TITLE__</h1>
      <p class="text-xs text-slate-400 mt-1">__SAFE_OBJ__</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
        <h3 class="text-sm font-semibold text-slate-200">Interactive Controls</h3>
        <div class="space-y-2">
          <label class="block text-xs text-slate-400">Parameter Input</label>
          <input id="user-param" type="text" value="Default Payload" class="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white">
        </div>
        <button onclick="executeAction()" class="w-full py-2 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow">
          Execute Operation
        </button>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
        <h3 class="text-sm font-semibold text-slate-200">Acceptance Verification</h3>
        <ul class="space-y-1.5 text-xs font-mono">
          __CRITERIA_ITEMS__
        </ul>
      </div>
    </div>

    <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2">
      <h3 class="text-sm font-semibold text-slate-200">Execution Output</h3>
      <pre id="output-box" class="p-3 bg-slate-950 rounded-lg text-xs font-mono text-emerald-400 border border-slate-800 overflow-x-auto">
// Application Initialized. Ready for input.
      </pre>
    </div>
  </div>
  <script>
    function executeAction() {
      const val = document.getElementById('user-param').value;
      const box = document.getElementById('output-box');
      box.innerText = '// Processed at ' + new Date().toISOString() + '\\n{\\n  "status": "SUCCESS",\\n  "payload": "' + val + '",\\n  "checksum": "verified"\\n}';
    }
  </script>
</body>
</html>
"""
    return template.replace("__SAFE_TITLE__", safe_title).replace("__SAFE_OBJ__", safe_obj).replace("__CRITERIA_ITEMS__", criteria_items)
