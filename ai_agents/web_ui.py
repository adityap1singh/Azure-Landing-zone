"""
Azure AI Deployment Center — Visual Web Command Dashboard
=========================================================
A modern, zero-dependency, real-time Web Command Center for orchestrating
Azure infrastructure and software application deployments via AI Agents.

Usage:
  python ai_agents/web_ui.py [--port 5000]
  or: python ai_agents/deploy_cli.py --web
"""

import os
import sys
import json
import time
import queue
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# ── Bootstrap ─────────────────────────────────────────────────────────────────
AGENTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = AGENTS_DIR.parent
sys.path.insert(0, str(AGENTS_DIR))

from dotenv import load_dotenv
load_dotenv(dotenv_path=AGENTS_DIR / '.env')

from deploy_cli import get_client, parse_intent, GEMINI_MODEL
from orchestrator import Orchestrator

# Global event queue for SSE streaming
EVENT_QUEUES: list[queue.Queue] = []
CURRENT_EXECUTION = {
    "running": False,
    "plan": None,
    "status": "idle",
    "logs": [],
}


def broadcast_event(event_type: str, data: dict):
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    CURRENT_EXECUTION["logs"].append({"type": event_type, "data": data, "ts": time.time()})
    for q in list(EVENT_QUEUES):
        try:
            q.put_nowait(msg)
        except Exception:
            if q in EVENT_QUEUES:
                EVENT_QUEUES.remove(q)


HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Azure AI Autonomous Deployment Center</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #090d16;
            --bg-card: rgba(18, 26, 43, 0.75);
            --bg-card-hover: rgba(28, 40, 65, 0.85);
            --border: rgba(56, 189, 248, 0.15);
            --border-hover: rgba(56, 189, 248, 0.35);
            --primary: #0284c7;
            --primary-glow: rgba(2, 132, 199, 0.4);
            --accent: #38bdf8;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-purple: #a855f7;
            --accent-red: #ef4444;
            --text-main: #f1f5f9;
            --text-dim: #94a3b8;
            --text-dark: #64748b;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: radial-gradient(circle at 50% 0%, #172554 0%, var(--bg-base) 75%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* ── Header ─────────────────────────────────────────── */
        header {
            padding: 1.25rem 2.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(12px);
            background: rgba(9, 13, 22, 0.8);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .logo-badge {
            background: linear-gradient(135deg, #0284c7, #6366f1);
            color: white;
            font-weight: 800;
            font-size: 1.2rem;
            padding: 8px 14px;
            border-radius: 12px;
            box-shadow: 0 0 20px var(--primary-glow);
        }

        .brand-title h1 {
            font-size: 1.25rem;
            font-weight: 700;
            background: linear-gradient(to right, #f8fafc, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-title p {
            font-size: 0.78rem;
            color: var(--text-dim);
        }

        .header-badges {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .badge {
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.25);
            color: var(--accent);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .badge.green {
            background: rgba(16, 185, 129, 0.1);
            border-color: rgba(16, 185, 129, 0.3);
            color: var(--accent-green);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
        }

        /* ── Main Container ─────────────────────────────────── */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem 2.5rem;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 2rem;
            flex: 1;
        }

        /* ── Hero Prompt Center ──────────────────────────────── */
        .prompt-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            backdrop-filter: blur(16px);
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }

        .prompt-card h2 {
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .prompt-input-wrapper {
            position: relative;
            display: flex;
            gap: 12px;
        }

        .prompt-input {
            flex: 1;
            background: rgba(10, 16, 30, 0.85);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 14px;
            padding: 1.1rem 1.4rem;
            color: white;
            font-family: inherit;
            font-size: 1rem;
            outline: none;
            transition: all 0.2s ease;
        }

        .prompt-input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 20px var(--primary-glow);
        }

        .btn-deploy {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: white;
            border: none;
            border-radius: 14px;
            padding: 0 2rem;
            font-family: inherit;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
            box-shadow: 0 0 20px var(--primary-glow);
        }

        .btn-deploy:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 30px var(--primary-glow);
            filter: brightness(1.1);
        }

        .btn-deploy:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        /* ── Preset Suggestions ─────────────────────────────── */
        .suggestions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
        }

        .suggestions-label {
            font-size: 0.8rem;
            color: var(--text-dark);
            font-weight: 600;
        }

        .pill {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: var(--text-dim);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.78rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .pill:hover {
            background: rgba(56, 189, 248, 0.15);
            border-color: var(--accent);
            color: var(--text-main);
        }

        /* ── Grid Layout ─────────────────────────────────────── */
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 2rem;
        }

        @media (max-width: 1024px) {
            .grid-2 { grid-template-columns: 1fr; }
        }

        /* ── Agent Pipeline Graph ────────────────────────────── */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1.75rem;
            backdrop-filter: blur(16px);
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .agent-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .agent-item {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 14px;
            padding: 1rem 1.25rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.2s ease;
        }

        .agent-item.active {
            border-color: var(--accent);
            background: rgba(2, 132, 199, 0.15);
            box-shadow: 0 0 15px var(--primary-glow);
        }

        .agent-item.done {
            border-color: var(--accent-green);
            background: rgba(16, 185, 129, 0.1);
        }

        .agent-info {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .agent-icon {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            font-weight: bold;
        }

        .agent-meta h4 {
            font-size: 0.95rem;
            font-weight: 600;
        }

        .agent-meta p {
            font-size: 0.75rem;
            color: var(--text-dim);
        }

        .agent-state {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.06);
            color: var(--text-dim);
        }

        .agent-state.active {
            background: rgba(56, 189, 248, 0.2);
            color: var(--accent);
        }

        .agent-state.done {
            background: rgba(16, 185, 129, 0.2);
            color: var(--accent-green);
        }

        /* ── Live Log Terminal ───────────────────────────────── */
        .terminal-card {
            background: #060911;
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 20px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            box-shadow: inset 0 0 30px rgba(0,0,0,0.8);
        }

        .terminal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 0.75rem;
        }

        .terminal-dots {
            display: flex;
            gap: 6px;
        }

        .dot { width: 10px; height: 10px; border-radius: 50%; }
        .dot.red { background: #ef4444; }
        .dot.yellow { background: #f59e0b; }
        .dot.green { background: #10b981; }

        .terminal-title {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--text-dim);
        }

        .terminal-output {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            line-height: 1.6;
            color: #cbd5e1;
            height: 380px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding-right: 8px;
        }

        .terminal-output::-webkit-scrollbar { width: 6px; }
        .terminal-output::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }

        .log-entry {
            display: flex;
            gap: 8px;
            word-break: break-all;
        }

        .log-entry .ts { color: var(--text-dark); font-size: 0.75rem; }
        .log-entry.INFO .status { color: var(--accent); }
        .log-entry.OK .status { color: var(--accent-green); }
        .log-entry.WARN .status { color: var(--accent-amber); }
        .log-entry.FAIL .status { color: var(--accent-red); }

        /* ── Plan Confirmation Modal / Banner ────────────────── */
        .plan-box {
            display: none;
            background: rgba(2, 132, 199, 0.1);
            border: 1px solid var(--accent);
            border-radius: 14px;
            padding: 1.25rem;
            margin-top: 1rem;
            flex-direction: column;
            gap: 12px;
        }

        .plan-box.show { display: flex; }

        .plan-summary {
            font-weight: 600;
            color: var(--accent);
            font-size: 0.95rem;
        }

        .plan-actions {
            display: flex;
            gap: 10px;
            margin-top: 8px;
        }

        .btn-confirm {
            background: var(--accent-green);
            color: black;
            font-weight: 700;
            padding: 8px 18px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
        }

        .btn-cancel {
            background: rgba(255,255,255,0.1);
            color: white;
            padding: 8px 18px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
        }

        /* ── Footer ─────────────────────────────────────────── */
        footer {
            padding: 1.5rem;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-dark);
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <div class="logo-badge">Azure AI</div>
            <div class="brand-title">
                <h1>Deployment Command Center</h1>
                <p>Autonomous LLM Agentic Cloud & Software Deployer</p>
            </div>
        </div>
        <div class="header-badges">
            <div class="badge green"><div class="status-dot"></div> Agents Active</div>
            <div class="badge">Model: gemini-2.5-flash</div>
        </div>
    </header>

    <div class="container">

        <!-- Prompt Section -->
        <div class="prompt-card">
            <h2>✨ What would you like to deploy to Azure?</h2>
            <div class="prompt-input-wrapper">
                <input type="text" id="promptInput" class="prompt-input" 
                       placeholder="e.g. Deploy a Python FastAPI microservice with Redis to Azure dev" />
                <button id="btnDeploy" class="btn-deploy" onclick="generatePlan()">
                    <span>🚀 Deploy</span>
                </button>
            </div>

            <!-- Quick Suggestions -->
            <div class="suggestions">
                <span class="suggestions-label">Suggestions:</span>
                <span class="pill" onclick="setPrompt('Deploy a Python FastAPI microservice with Redis to Azure dev')">FastAPI + Redis (Dev)</span>
                <span class="pill" onclick="setPrompt('Deploy a fullstack React frontend and Node.js backend to AKS')">Fullstack React + Node (AKS)</span>
                <span class="pill" onclick="setPrompt('Deploy high-performance Go API to Azure dev')">Golang Gin Microservice</span>
                <span class="pill" onclick="setPrompt('Deploy an Nginx web application with landing page')">Nginx Web App</span>
                <span class="pill" onclick="setPrompt('Audit and provision Azure Landing Zone infrastructure in dev')">Terraform Landing Zone</span>
                <span class="pill" onclick="setPrompt('Run full CI/CD pipeline check, auto-diagnose and fix failures')">Pipeline Auto-Fix</span>
            </div>

            <!-- Plan Confirmation Area -->
            <div id="planBox" class="plan-box">
                <div id="planSummary" class="plan-summary"></div>
                <div id="planStepsList" style="font-size: 0.85rem; color: #cbd5e1;"></div>
                <div class="plan-actions">
                    <button class="btn-confirm" onclick="confirmAndExecute()">⚡ Confirm & Run Plan</button>
                    <button class="btn-cancel" onclick="cancelPlan()">Cancel</button>
                </div>
            </div>
        </div>

        <!-- Grid: Agent Pipeline + Live Terminal -->
        <div class="grid-2">

            <!-- Agent Network Card -->
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">🤖 Active Agent Pipeline</h3>
                    <span id="pipelineStatusBadge" class="badge">Idle</span>
                </div>

                <div class="agent-list">
                    <!-- App Scaffolder Agent -->
                    <div id="agent-app_agent" class="agent-item">
                        <div class="agent-info">
                            <div class="agent-icon">📦</div>
                            <div class="agent-meta">
                                <h4>App Scaffolder Agent</h4>
                                <p>Inspects/Generates Code, Dockerfile & K8s Manifests</p>
                            </div>
                        </div>
                        <div id="status-app_agent" class="agent-state">Standby</div>
                    </div>

                    <!-- Terraform Agent -->
                    <div id="agent-terraform_agent" class="agent-item">
                        <div class="agent-info">
                            <div class="agent-icon">🏗️</div>
                            <div class="agent-meta">
                                <h4>Terraform Infrastructure Agent</h4>
                                <p>Audits, Fixes & Provisions Azure Landing Zone</p>
                            </div>
                        </div>
                        <div id="status-terraform_agent" class="agent-state">Standby</div>
                    </div>

                    <!-- K8s / ACR Agent -->
                    <div id="agent-k8s_acr_agent" class="agent-item">
                        <div class="agent-info">
                            <div class="agent-icon">☸️</div>
                            <div class="agent-meta">
                                <h4>Kubernetes & ACR Agent</h4>
                                <p>ACR Container Build & AKS Manifest Rollout</p>
                            </div>
                        </div>
                        <div id="status-k8s_acr_agent" class="agent-state">Standby</div>
                    </div>

                    <!-- Pipeline Agent -->
                    <div id="agent-pipeline_agent" class="agent-item">
                        <div class="agent-info">
                            <div class="agent-icon">🔄</div>
                            <div class="agent-meta">
                                <h4>Pipeline / CI-CD Agent</h4>
                                <p>GitHub Actions Health Monitor & Auto-Rerunner</p>
                            </div>
                        </div>
                        <div id="status-pipeline_agent" class="agent-state">Standby</div>
                    </div>
                </div>
            </div>

            <!-- Terminal Output Card -->
            <div class="terminal-card">
                <div class="terminal-header">
                    <div class="terminal-dots">
                        <div class="dot red"></div>
                        <div class="dot yellow"></div>
                        <div class="dot green"></div>
                    </div>
                    <div class="terminal-title">live-agent-stream.log</div>
                    <div style="font-size: 0.75rem; color: var(--text-dark);">SSE Real-Time</div>
                </div>
                <div id="terminalOutput" class="terminal-output">
                    <div class="log-entry INFO">
                        <span class="ts">[00:00:00]</span>
                        <span class="status">ℹ</span>
                        <span>Azure AI Deployment Center initialized and ready. Type a prompt above.</span>
                    </div>
                </div>
            </div>

        </div>

    </div>

    <footer>
        Azure Landing Zone Multi-Agent Orchestration • Powered by Google Gemini & Azure Cloud
    </footer>

    <script>
        let currentPlan = null;
        let eventSource = null;

        function setPrompt(text) {
            document.getElementById('promptInput').value = text;
        }

        function appendLog(status, message) {
            const out = document.getElementById('terminalOutput');
            const now = new Date().toTimeString().split(' ')[0];
            const div = document.createElement('div');
            div.className = `log-entry ${status}`;
            div.innerHTML = `<span class="ts">[${now}]</span> <span class="status">${status === 'OK' ? '✅' : (status === 'FAIL' ? '❌' : (status === 'WARN' ? '⚠️' : 'ℹ'))}</span> <span>${message}</span>`;
            out.appendChild(div);
            out.scrollTop = out.scrollHeight;
        }

        function connectSSE() {
            if (eventSource) return;
            eventSource = new EventSource('/api/events');
            
            eventSource.addEventListener('log', (e) => {
                const payload = JSON.parse(e.data);
                const entry = payload.entry || {};
                appendLog(entry.status || 'INFO', entry.event || JSON.stringify(entry));
            });

            eventSource.addEventListener('step_start', (e) => {
                const payload = JSON.parse(e.data);
                const step = payload.step || {};
                setAgentState(step.agent, 'active', 'Running…');
            });

            eventSource.addEventListener('step_end', (e) => {
                const payload = JSON.parse(e.data);
                const step = payload.step || {};
                setAgentState(step.agent, payload.success ? 'done' : 'fail', payload.success ? 'Complete' : 'Failed');
            });

            eventSource.addEventListener('plan_complete', (e) => {
                const payload = JSON.parse(e.data);
                document.getElementById('pipelineStatusBadge').textContent = payload.result.success ? '✅ Success' : '⚠️ Failed';
                document.getElementById('btnDeploy').disabled = false;
                appendLog(payload.result.success ? 'OK' : 'WARN', 'Multi-agent orchestration workflow completed.');
            });
        }

        function setAgentState(agentId, state, text) {
            const card = document.getElementById(`agent-${agentId}`);
            const badge = document.getElementById(`status-${agentId}`);
            if (!card || !badge) return;

            card.classList.remove('active', 'done');
            badge.classList.remove('active', 'done');

            if (state === 'active') {
                card.classList.add('active');
                badge.classList.add('active');
            } else if (state === 'done') {
                card.classList.add('done');
                badge.classList.add('done');
            }
            badge.textContent = text;
        }

        async function generatePlan() {
            const prompt = document.getElementById('promptInput').value.trim();
            if (!prompt) return;

            connectSSE();
            const btn = document.getElementById('btnDeploy');
            btn.disabled = true;
            btn.textContent = '🧠 Planning…';

            appendLog('INFO', `Planning deployment: "${prompt}"`);

            try {
                const res = await fetch('/api/plan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt })
                });
                const data = await res.json();
                if (data.error) {
                    appendLog('FAIL', `Plan error: ${data.error}`);
                    btn.disabled = false;
                    btn.textContent = '🚀 Deploy';
                    return;
                }

                currentPlan = data.plan;
                displayPlanUI(currentPlan);
                btn.textContent = '🚀 Deploy';
                btn.disabled = false;
            } catch (err) {
                appendLog('FAIL', `Network error: ${err}`);
                btn.disabled = false;
                btn.textContent = '🚀 Deploy';
            }
        }

        function displayPlanUI(plan) {
            const box = document.getElementById('planBox');
            const summary = document.getElementById('planSummary');
            const stepsList = document.getElementById('planStepsList');

            summary.textContent = `📋 ${plan.intent_summary || 'Execution Plan'}`;
            let html = '<ul style="margin-left: 20px; margin-top: 8px;">';
            (plan.steps || []).forEach(s => {
                html += `<li><strong>Step ${s.step}: [${s.agent}]</strong> — ${s.reason}</li>`;
            });
            html += '</ul>';
            stepsList.innerHTML = html;
            box.classList.add('show');
        }

        function cancelPlan() {
            currentPlan = null;
            document.getElementById('planBox').classList.remove('show');
            appendLog('INFO', 'Plan execution cancelled.');
        }

        async function confirmAndExecute() {
            if (!currentPlan) return;
            document.getElementById('planBox').classList.remove('show');
            document.getElementById('btnDeploy').disabled = true;
            document.getElementById('pipelineStatusBadge').textContent = 'Executing';

            appendLog('INFO', 'Executing multi-agent plan on Azure…');

            try {
                await fetch('/api/deploy', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plan: currentPlan })
                });
            } catch (err) {
                appendLog('FAIL', `Execution error: ${err}`);
            }
        }

        // Initialize SSE connection on load
        window.addEventListener('DOMContentLoaded', () => {
            connectSSE();
        });
    </script>
</body>
</html>
"""


class WebRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default noisy console logs

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))

        elif parsed.path == "/api/events":
            self.send_response(200)
            self.send_header("Content-type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            q = queue.Queue()
            EVENT_QUEUES.append(q)
            try:
                # Send welcome ping
                self.wfile.write(f"event: log\ndata: {json.dumps({'entry': {'status': 'INFO', 'event': 'Connected to live event stream'}})}\n\n".encode("utf-8"))
                self.wfile.flush()
                while True:
                    msg = q.get()
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
            except Exception:
                if q in EVENT_QUEUES:
                    EVENT_QUEUES.remove(q)

        elif parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(CURRENT_EXECUTION).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        data = json.loads(post_data)

        if parsed.path == "/api/plan":
            prompt = data.get("prompt", "")
            try:
                client = get_client()
                plan = parse_intent(client, prompt, dry_run=False)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "plan": plan}).encode("utf-8"))
            except Exception as exc:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(exc)}).encode("utf-8"))

        elif parsed.path == "/api/deploy":
            plan = data.get("plan")
            if not plan:
                self.send_response(400)
                self.end_headers()
                return

            def background_run():
                CURRENT_EXECUTION["running"] = True
                CURRENT_EXECUTION["plan"] = plan
                orch = Orchestrator(event_listener=lambda evt: broadcast_event(evt.get("type", "log"), evt))
                result = orch.execute_plan(plan)
                CURRENT_EXECUTION["running"] = False
                CURRENT_EXECUTION["status"] = "success" if result.get("success") else "failed"

            threading.Thread(target=background_run, daemon=True).start()

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "status": "started"}).encode("utf-8"))


def start_web_server(port: int = 5000):
    server = HTTPServer(("0.0.0.0", port), WebRequestHandler)
    print("\n" + "═" * 70)
    print(f"  🌐  Azure AI Deployment Command Center Web UI is LIVE!")
    print(f"  👉  Open in your browser: http://localhost:{port}")
    print("═" * 70 + "\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Web UI server…")
        server.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Azure AI Web Command Center")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
    args = parser.parse_args()
    start_web_server(port=args.port)
