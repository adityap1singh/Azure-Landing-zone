"""
AI Orchestration Layer — The Central Brain
==========================================
Connects Gemini LLM + Pipeline Agent + Terraform Agent + K8s/ACR Agent +
GitHub CLI (gh) into a single coordinated execution engine.

Responsibilities:
  • Execute structured plans produced by deploy_cli.py
  • Run GitHub operations from the terminal via `gh` CLI
  • Pass shared context (e.g. built image URI) between agent steps
  • Write a full session_log.json after every run for auditability
  • Provide a standalone API so agents can call each other programmatically

Usage (programmatic):
  from orchestrator import Orchestrator
  orch = Orchestrator()
  orch.execute_plan(plan_dict)

Usage (standalone GitHub operations):
  python orchestrator.py --gh-status          # last pipeline run status
  python orchestrator.py --gh-trigger main    # trigger workflow on branch
  python orchestrator.py --gh-logs            # print latest run logs
  python orchestrator.py --gh-pr "title" "body" "head-branch"  # open PR
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from google import genai
from dotenv import load_dotenv

# ── Bootstrap ────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv(dotenv_path=Path(__file__).parent / '.env')

GEMINI_MODEL = "gemini-2.5-flash"
AGENTS_DIR   = Path(__file__).parent
REPO_ROOT    = AGENTS_DIR.parent
LOG_FILE     = AGENTS_DIR / "session_log.json"


def _env(name: str, default: str = None, required: bool = False) -> str:
    val = os.getenv(name, default)
    if required and not val:
        print(f"[ERROR] Required env var '{name}' not set.")
        sys.exit(1)
    return val


def _gemini_client() -> genai.Client:
    return genai.Client(api_key=_env("GEMINI_API_KEY", required=True))


# ── Session Logger ────────────────────────────────────────────────────────────

class SessionLogger:
    """Append-only JSON log for every orchestrator action with live event streaming."""

    def __init__(self, path: Path = LOG_FILE, event_listener=None):
        self.path = path
        self.event_listener = event_listener
        self._entries: list[dict] = []

    def log(self, event: str, detail: Any = None, status: str = "INFO"):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "event": event,
            "detail": detail,
        }
        self._entries.append(entry)
        icon = {"INFO": "ℹ", "OK": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(status, "•")
        print(f"  {icon} [{status}] {event}")
        if self.event_listener:
            try:
                self.event_listener({"type": "log", "entry": entry})
            except Exception:
                pass

    def save(self):
        existing = []
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        all_entries = existing + self._entries
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(all_entries, f, indent=2, default=str)
        print(f"\n  📄 Session log saved → {self.path.relative_to(REPO_ROOT)}")


# ── GitHub CLI Integration ────────────────────────────────────────────────────

class GitHubCLI:
    """
    Wraps the `gh` CLI for pipeline and repository operations.
    All commands run via terminal subprocess — no GitHub API tokens needed
    (authentication is handled by `gh auth login` which the user does once).
    """

    def __init__(self, repo: str = None, logger: SessionLogger = None):
        self.repo = repo or _env("GITHUB_REPOSITORY", "")
        self.logger = logger or SessionLogger()
        self._check_gh_installed()

    def _check_gh_installed(self):
        try:
            result = subprocess.run(
                ["gh", "--version"], capture_output=True, text=True
            )
            self._available = (result.returncode == 0)
            if not self._available:
                print("  [WARN] `gh` CLI not found. Install from https://cli.github.com/")
                print("         GitHub operations will be skipped.")
        except (FileNotFoundError, Exception):
            print("  [WARN] `gh` CLI not found. Install from https://cli.github.com/")
            print("         GitHub operations will be skipped.")
            self._available = False

    def _run(self, args: list[str], capture: bool = True) -> tuple[int, str, str]:
        if not self._available:
            return 1, "", "gh CLI not available"
        cmd = ["gh"] + args
        print(f"  [gh] {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=capture, text=True)
        if result.stdout:
            print(result.stdout[-2000:])
        if result.stderr and result.returncode != 0:
            print(result.stderr[-500:])
        return result.returncode, result.stdout, result.stderr

    # ── Workflow / Pipeline operations ────────────────────────────────────────

    def get_run_status(self) -> dict | None:
        """Return the latest workflow run as a dict."""
        rc, stdout, _ = self._run([
            "run", "list", "--limit", "1",
            "--repo", self.repo,
            "--json", "databaseId,status,conclusion,name,number,url",
        ])
        if rc != 0 or not stdout.strip():
            return None
        try:
            runs = json.loads(stdout)
            return runs[0] if runs else None
        except Exception:
            return None

    def trigger_workflow(self, workflow_file: str = "cd.yaml", branch: str = "main") -> bool:
        """Trigger a GitHub Actions workflow via gh CLI."""
        self.logger.log(f"Triggering workflow '{workflow_file}' on branch '{branch}'")
        rc, _, _ = self._run([
            "workflow", "run", workflow_file,
            "--ref", branch,
            "--repo", self.repo,
        ])
        return rc == 0

    def get_run_logs(self, run_id: int = None) -> str:
        """Fetch logs for the latest (or specific) run."""
        if run_id:
            rc, stdout, _ = self._run(["run", "view", str(run_id), "--log", "--repo", self.repo])
        else:
            rc, stdout, _ = self._run(["run", "view", "--log", "--repo", self.repo])
        return stdout if rc == 0 else ""

    def watch_run(self, run_id: int = None) -> bool:
        """Stream live run output and return True on success."""
        args = ["run", "watch", "--repo", self.repo]
        if run_id:
            args.append(str(run_id))
        rc, _, _ = self._run(args, capture=False)
        return rc == 0

    def create_pr(self, title: str, body: str, head: str, base: str = "main") -> str | None:
        """Create a PR and return the PR URL."""
        self.logger.log(f"Creating PR: '{title}' from '{head}' → '{base}'")
        rc, stdout, _ = self._run([
            "pr", "create",
            "--title", title,
            "--body", body,
            "--head", head,
            "--base", base,
            "--repo", self.repo,
        ])
        if rc == 0:
            url = stdout.strip()
            self.logger.log(f"PR created: {url}", status="OK")
            return url
        return None

    def git_commit_push(self, message: str, branch: str) -> bool:
        """Stage all changes, commit, and push to origin from terminal."""
        self.logger.log(f"Committing and pushing to branch '{branch}'")
        cmds = [
            ["git", "checkout", "-B", branch],
            ["git", "add", "."],
            ["git", "commit", "-m", message],
            ["git", "push", "--force-with-lease", "origin", branch],
        ]
        for cmd in cmds:
            print(f"  [git] {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
            if result.returncode != 0:
                print(f"  [FAIL] {result.stderr[:300]}")
                return False
        self.logger.log(f"Pushed branch '{branch}' to origin", status="OK")
        return True


# ── Agent Runners ─────────────────────────────────────────────────────────────

class AgentRunner:
    """
    Runs each specialised agent in-process with shared context propagation.
    """

    def __init__(self, logger: SessionLogger, shared_ctx: dict):
        self.logger = logger
        self.ctx = shared_ctx   # shared mutable dict for cross-agent context

    def _import_agent(self, agent_id: str):
        """Dynamically import an agent module from the agents directory."""
        agent_paths = {
            "app_agent":       AGENTS_DIR / "app_agent"       / "app_agent.py",
            "pipeline_agent":  AGENTS_DIR / "pipeline_agent"  / "pipeline_agent.py",
            "terraform_agent": AGENTS_DIR / "terraform_agent" / "terraform_agent.py",
            "k8s_acr_agent":   AGENTS_DIR / "k8s_acr_agent"   / "k8s_acr_agent.py",
        }
        path = agent_paths.get(agent_id)
        if not path or not path.exists():
            raise ImportError(f"Agent module not found: {agent_id} at {path}")
        import importlib.util
        spec = importlib.util.spec_from_file_location(agent_id, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def run_app_agent(self, args: dict) -> bool:
        self.logger.log("Running App Scaffolder / Manifest Agent", args)
        try:
            mod = self._import_agent("app_agent")
            agent = mod.AppAgent(dry_run=args.get("dry_run", False))
            merged_args = {**self.ctx, **args}
            result = agent.run(merged_args)
            if isinstance(result, dict) and result.get("success"):
                # Save output context so subsequent agents (ACR, K8s, Terraform) have it
                self.ctx.update(result)
                self.logger.log("App Agent complete", detail=result, status="OK")
                return True
            self.logger.log("App Agent returned unsuccessful status", detail=result, status="FAIL")
            return False
        except Exception as exc:
            self.logger.log(f"App Agent error: {exc}", status="FAIL")
            return False

    def run_pipeline_agent(self, args: dict) -> bool:
        self.logger.log("Running Pipeline Agent", args)
        try:
            mod = self._import_agent("pipeline_agent")
            agent = mod.PipelineAgent(dry_run=args.get("dry_run", False))
            agent.max_retries = int(args.get("max_retries", 3))
            agent.run()
            self.logger.log("Pipeline Agent complete", status="OK")
            return True
        except Exception as exc:
            self.logger.log(f"Pipeline Agent error: {exc}", status="FAIL")
            return False

    def run_terraform_agent(self, args: dict) -> bool:
        self.logger.log("Running Terraform Agent", args)
        try:
            mod = self._import_agent("terraform_agent")
            merged_args = {**self.ctx, **args}
            if hasattr(mod, "TerraformAgent"):
                agent = mod.TerraformAgent(dry_run=args.get("dry_run", False))
                ok = agent.run(merged_args)
            else:
                original_argv = sys.argv
                sys.argv = [
                    "terraform_agent.py",
                    "--env", merged_args.get("env", "dev"),
                    "--max-retries", str(merged_args.get("max_retries", 3)),
                ]
                if merged_args.get("dry_run"):
                    sys.argv.append("--dry-run")
                if merged_args.get("audit_only"):
                    sys.argv.append("--audit-only")
                try:
                    mod.main()
                    ok = True
                finally:
                    sys.argv = original_argv
            self.logger.log("Terraform Agent complete", status="OK" if ok else "FAIL")
            return ok
        except SystemExit as exc:
            ok = exc.code == 0
            self.logger.log("Terraform Agent exited", detail=str(exc.code),
                            status="OK" if ok else "FAIL")
            return ok
        except Exception as exc:
            self.logger.log(f"Terraform Agent error: {exc}", status="FAIL")
            return False

    def run_k8s_acr_agent(self, args: dict) -> bool:
        self.logger.log("Running K8s/ACR Agent", args)
        try:
            mod = self._import_agent("k8s_acr_agent")
            # Automatically feed context from AppAgent if not explicitly passed
            merged_args = {
                "image_name": self.ctx.get("app_name") or "app",
                "build_context_dir": self.ctx.get("app_dir"),
                "port": self.ctx.get("port"),
                "namespace": self.ctx.get("namespace", "default"),
                **args,
            }
            if hasattr(mod, "K8sAcrAgent"):
                agent = mod.K8sAcrAgent(dry_run=args.get("dry_run", False))
                ok = agent.run(merged_args)
            else:
                original_argv = sys.argv
                sys.argv = ["k8s_acr_agent.py", "--max-retries", str(args.get("max_retries", 3))]
                if args.get("dry_run"):
                    sys.argv.append("--dry-run")
                if args.get("skip_build"):
                    sys.argv.append("--skip-build")
                if args.get("skip_deploy"):
                    sys.argv.append("--skip-deploy")
                try:
                    mod.main()
                    ok = True
                finally:
                    sys.argv = original_argv
            self.logger.log("K8s/ACR Agent complete", status="OK" if ok else "FAIL")
            return ok
        except SystemExit as exc:
            ok = exc.code == 0
            self.logger.log("K8s/ACR Agent exited", detail=str(exc.code),
                            status="OK" if ok else "FAIL")
            return ok
        except Exception as exc:
            self.logger.log(f"K8s/ACR Agent error: {exc}", status="FAIL")
            return False

    def run_step(self, step: dict) -> bool:
        agent = step.get("agent")
        step_args = step.get("args", {})
        dispatch = {
            "app_agent":       self.run_app_agent,
            "pipeline_agent":  self.run_pipeline_agent,
            "terraform_agent": self.run_terraform_agent,
            "k8s_acr_agent":   self.run_k8s_acr_agent,
        }
        fn = dispatch.get(agent)
        if not fn:
            self.logger.log(f"Unknown agent: '{agent}'", status="WARN")
            return False
        return fn(step_args)


# ── Orchestrator ──────────────────────────────────────────────────────────────

class Orchestrator:
    """
    Central coordinator. Executes a structured plan produced by deploy_cli.py
    or supplied directly. Wires LLM + Agents + GitHub CLI together.
    """

    def __init__(self, event_listener=None):
        self.event_listener = event_listener
        self.logger  = SessionLogger(event_listener=event_listener)
        self.client  = _gemini_client()
        self.ctx     = {}   # shared context dict passed between steps
        self.gh      = GitHubCLI(logger=self.logger)
        self.runner  = AgentRunner(logger=self.logger, shared_ctx=self.ctx)

    def execute_plan(self, plan: dict) -> dict:
        """
        Execute every step in the plan sequentially.
        Returns a result dict with 'success' bool and per-step outcomes.
        """
        intent   = plan.get("intent_summary", "Deploy")
        steps    = plan.get("steps", [])
        warnings = plan.get("warnings", [])

        print("\n" + "═" * 65)
        print(f"  🚀  Orchestrator — Executing Plan")
        print(f"  Intent: {intent}")
        print(f"  Steps : {len(steps)}")
        print("═" * 65)

        self.logger.log(f"Plan start: {intent}", detail={"steps": len(steps)})
        for w in warnings:
            self.logger.log(f"Warning: {w}", status="WARN")

        outcomes = []
        all_ok = True
        start_ts = time.time()

        for step in steps:
            step_num = step.get("step", "?")
            agent    = step.get("agent", "?")
            reason   = step.get("reason", "")
            print(f"\n{'─'*65}")
            print(f"  Step {step_num}/{len(steps)}: [{agent}]")
            print(f"  Reason: {reason}")
            print(f"{'─'*65}")

            if self.event_listener:
                self.event_listener({"type": "step_start", "step": step})

            self.logger.log(f"Step {step_num} start: {agent}", detail=step.get("args"))
            ok = self.runner.run_step(step)
            outcomes.append({"step": step_num, "agent": agent, "success": ok})

            if self.event_listener:
                self.event_listener({"type": "step_end", "step": step, "success": ok})

            if not ok:
                all_ok = False
                self.logger.log(
                    f"Step {step_num} FAILED — consulting Gemini for recovery guidance",
                    status="WARN"
                )
                if not self._try_recover(step):
                    print(f"  ⛔ Step {step_num} could not be recovered. Continuing to next step.")

        elapsed = round(time.time() - start_ts, 1)
        self.logger.log(
            f"Plan complete — {'SUCCESS' if all_ok else 'PARTIAL FAILURE'} in {elapsed}s",
            detail=outcomes,
            status="OK" if all_ok else "FAIL",
        )
        self.logger.save()

        # Final summary
        print("\n" + "═" * 65)
        print(f"  {'✅ All steps succeeded' if all_ok else '⚠️  Some steps failed'}")
        for o in outcomes:
            icon = "✅" if o["success"] else "❌"
            print(f"    {icon} Step {o['step']}: {o['agent']}")
        print(f"  ⏱  Total time: {elapsed}s")
        print("═" * 65)

        res = {"success": all_ok, "outcomes": outcomes, "elapsed_sec": elapsed, "context": self.ctx}
        if self.event_listener:
            self.event_listener({"type": "plan_complete", "result": res})
        return res

    def _try_recover(self, failed_step: dict) -> bool:
        """
        Ask Gemini for recovery suggestions when a step fails,
        then attempt a simplified retry.
        """
        agent = failed_step.get("agent")
        args  = failed_step.get("args", {})
        prompt = f"""An agent step failed during orchestration.
Agent: {agent}
Args:  {json.dumps(args)}

Suggest a recovery action in plain text (1-2 sentences).
Should we: retry with different args, skip this step, or abort the whole plan?
"""
        try:
            resp = self.client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            guidance = resp.text.strip()
            print(f"\n  🤖 Gemini Recovery Guidance:\n  {guidance}\n")
            self.logger.log("Recovery guidance", detail=guidance)
        except Exception:
            pass
        return False   # orchestrator logs the guidance but doesn't auto-retry here


# ── Standalone GitHub CLI operations ─────────────────────────────────────────

def standalone_gh(args):
    logger = SessionLogger()
    gh = GitHubCLI(logger=logger)

    if args.gh_status:
        run = gh.get_run_status()
        if run:
            print(json.dumps(run, indent=2))
        else:
            print("No recent runs found.")

    elif args.gh_trigger:
        branch = args.gh_trigger
        ok = gh.trigger_workflow(branch=branch)
        print("✅ Triggered." if ok else "❌ Failed to trigger.")

    elif args.gh_logs:
        logs = gh.get_run_logs()
        print(logs or "(no logs)")

    elif args.gh_pr:
        title, body, head = args.gh_pr
        url = gh.create_pr(title, body, head)
        print(f"PR: {url}" if url else "Failed to create PR.")

    logger.save()


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Orchestration Layer — GitHub CLI + Agent Coordinator"
    )
    parser.add_argument("--gh-status",  action="store_true",
                        help="Print latest GitHub Actions run status")
    parser.add_argument("--gh-trigger", metavar="BRANCH",
                        help="Trigger the CD workflow on BRANCH")
    parser.add_argument("--gh-logs",    action="store_true",
                        help="Print logs from the latest workflow run")
    parser.add_argument("--gh-pr",     nargs=3, metavar=("TITLE", "BODY", "HEAD"),
                        help="Create a GitHub Pull Request from HEAD into main")
    args = parser.parse_args()

    if any([args.gh_status, args.gh_trigger, args.gh_logs, args.gh_pr]):
        standalone_gh(args)
    else:
        parser.print_help()
