"""
Pipeline Agent — GitHub Actions Monitor, Auto-Fixer & Rerunner
==============================================================
Responsibilities:
  1. Monitor the latest GitHub Actions workflow run.
  2. On failure → fetch logs → ask Gemini to diagnose and produce corrected files.
  3. Apply fixes to disk → commit → push to a fix branch → re-trigger the run via GitHub API.
  4. Wait for the re-triggered run to complete, then repeat until success or MAX_RETRIES.

Environment variables (set in ai_agents/.env):
  GEMINI_API_KEY        — Google Gemini API key
  GITHUB_TOKEN          — GitHub personal access token (repo + workflow scopes)
  GITHUB_REPOSITORY     — e.g. "my-org/my-repo"
  MAX_RETRIES           — Max number of auto-fix-rerun cycles (default: 3)
"""

import os
import sys
import json
import time
import subprocess
import requests
from google import genai
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_MAX_RETRIES = 3
POLL_INTERVAL_SEC = 20   # seconds between status polls


def get_env(name, default=None, required=False):
    val = os.getenv(name, default)
    if required and not val:
        print(f"[ERROR] Required env variable '{name}' is not set.")
        sys.exit(1)
    return val


def run_git(args, cwd=None):
    """Run a git command and return the CompletedProcess result."""
    cmd = ['git'] + args
    print(f"  [git] {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def detect_repo_from_git() -> str:
    """Auto-detect owner/repo from terminal git remote."""
    try:
        res = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
        url = res.stdout.strip()
        if "github.com" in url:
            # handle https://github.com/owner/repo.git or git@github.com:owner/repo.git
            clean = url.split("github.com")[-1].replace(":", "/").strip("/")
            if clean.endswith(".git"):
                clean = clean[:-4]
            return clean
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# PipelineAgent
# ---------------------------------------------------------------------------
class PipelineAgent:
    """
    Monitors GitHub Actions pipelines, auto-fixes failures with Gemini,
    commits the fix, and re-triggers the run via terminal git/gh CLI or API.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.github_token = get_env("GITHUB_TOKEN", default="")
        self.repo = get_env("GITHUB_REPOSITORY", default="") or detect_repo_from_git()
        self.max_retries = int(get_env("MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))
        
        try:
            from llm_client import get_gemini_client
            self.gemini_client = get_gemini_client()
        except Exception:
            self.gemini_client = genai.Client(api_key=get_env("GEMINI_API_KEY", required=True))

        self.repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.github_token:
            self.headers["Authorization"] = f"Bearer {self.github_token}"

    # ------------------------------------------------------------------
    # GitHub CLI / API helpers
    # ------------------------------------------------------------------

    def _gh_get(self, path: str) -> requests.Response:
        if self.github_token:
            url = f"https://api.github.com/repos/{self.repo}{path}"
            return requests.get(url, headers=self.headers, timeout=30)
        return None

    def _gh_post(self, path: str, data: dict = None) -> requests.Response:
        if self.github_token:
            url = f"https://api.github.com/repos/{self.repo}{path}"
            return requests.post(url, headers=self.headers, json=data or {}, timeout=30)
        return None

    # ------------------------------------------------------------------
    # Step 1 — Get latest workflow run
    # ------------------------------------------------------------------

    def get_latest_run(self) -> dict | None:
        """Return the most recent workflow run object, using terminal gh CLI or API."""
        print(f"\n[Pipeline Agent] Fetching latest workflow run for '{self.repo}' via terminal gh CLI / API…")

        # 1. Try terminal gh CLI
        try:
            res = subprocess.run(
                ["gh", "run", "list", "--limit", "1", "--repo", self.repo,
                 "--json", "databaseId,status,conclusion,name,number,url"],
                capture_output=True, text=True
            )
            if res.returncode == 0 and res.stdout.strip():
                runs = json.loads(res.stdout)
                if runs:
                    r = runs[0]
                    return {
                        "id": r.get("databaseId"),
                        "name": r.get("name"),
                        "run_number": r.get("number"),
                        "status": r.get("status"),
                        "conclusion": r.get("conclusion"),
                        "html_url": r.get("url"),
                    }
        except (FileNotFoundError, Exception):
            pass

        # 2. Fallback to API if token present
        resp = self._gh_get("/actions/runs") if self.github_token else None
        if resp and resp.status_code == 200:
            runs = resp.json().get("workflow_runs", [])
            if runs:
                return runs[0]

        print("  [INFO] No workflow runs found or gh CLI not logged in.")
        return None

    # ------------------------------------------------------------------
    # Step 2 — Wait for a run to reach a terminal state
    # ------------------------------------------------------------------

    def wait_for_run(self, run_id: int, timeout_sec: int = 900) -> dict | None:
        """
        Poll until the given run_id is no longer 'in_progress' or 'queued'.
        Returns the final run dict, or None on timeout/error.
        """
        print(f"\n[Pipeline Agent] Waiting for run #{run_id} to complete…")
        elapsed = 0
        while elapsed < timeout_sec:
            resp = self._gh_get(f"/actions/runs/{run_id}")
            if resp.status_code != 200:
                print(f"  [ERROR] Polling run: {resp.status_code}")
                return None

            run = resp.json()
            status = run.get("status")
            conclusion = run.get("conclusion")
            print(f"  [{elapsed:>4}s] status={status} conclusion={conclusion}")

            if status in ("completed", "action_required", "cancelled", "timed_out"):
                return run

            time.sleep(POLL_INTERVAL_SEC)
            elapsed += POLL_INTERVAL_SEC

        print("  [WARN] Timed out waiting for run to complete.")
        return None

    # ------------------------------------------------------------------
    # Step 3 — Collect failure logs
    # ------------------------------------------------------------------

    def get_failure_logs(self, run_id: int) -> str:
        """Return concatenated log text from all failed jobs in the run via terminal gh CLI or API."""
        print(f"\n[Pipeline Agent] Collecting failure logs from run #{run_id} via terminal gh CLI / API…")

        # 1. Try terminal gh CLI
        try:
            res = subprocess.run(
                ["gh", "run", "view", str(run_id), "--log", "--repo", self.repo],
                capture_output=True, text=True
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = res.stdout.splitlines()
                return "\n".join(lines[-2000:])
        except (FileNotFoundError, Exception):
            pass

        # 2. Fallback to API if token present
        if self.github_token:
            resp = self._gh_get(f"/actions/runs/{run_id}/jobs")
            if resp and resp.status_code == 200:
                jobs = resp.json().get("jobs", [])
                failed_logs = []
                for job in jobs:
                    if job.get("conclusion") != "failure":
                        continue
                    job_id = job["id"]
                    job_name = job["name"]
                    print(f"  Failed job: '{job_name}' (id={job_id})")

                    log_resp = requests.get(
                        f"https://api.github.com/repos/{self.repo}/actions/jobs/{job_id}/logs",
                        headers=self.headers,
                        timeout=60,
                    )
                    if log_resp.status_code == 200:
                        lines = log_resp.text.splitlines()
                        truncated = "\n".join(lines[-2000:])
                        failed_logs.append(f"=== Job: {job_name} ===\n{truncated}")
                    else:
                        failed_logs.append(
                            f"=== Job: {job_name} ===\n[Logs unavailable: {log_resp.status_code}]"
                        )
                if failed_logs:
                    return "\n\n".join(failed_logs)

        return "No failed job logs available."

    # ------------------------------------------------------------------
    # Step 4 — Gemini diagnosis + file corrections
    # ------------------------------------------------------------------

    def diagnose_and_fix(self, logs: str) -> dict | None:
        """
        Send failure logs (+ all .tf and .yaml files) to Gemini.
        Returns a dict with 'diagnosis' and 'corrections' list, or None on failure.
        """
        # Gather relevant source files for context
        context_files = {}
        for walk_root, _, files in os.walk(self.repo_root):
            # Skip hidden dirs (.git, .github) and node_modules
            parts = os.path.relpath(walk_root, self.repo_root).split(os.sep)
            if any(p.startswith('.') for p in parts):
                continue
            for fname in files:
                if fname.endswith(('.tf', '.yaml', '.yml', '.py', 'Dockerfile', 'dockerfile')):
                    full = os.path.join(walk_root, fname)
                    rel = os.path.relpath(full, self.repo_root)
                    try:
                        with open(full, 'r', encoding='utf-8', errors='replace') as fh:
                            context_files[rel] = fh.read()
                    except Exception:
                        pass

        file_context = "\n\n".join(
            f"--- FILE: {path} ---\n{content}" for path, content in context_files.items()
        )

        prompt = f"""You are a senior DevOps and cloud infrastructure engineer specialising in
Azure, Terraform, Kubernetes, and GitHub Actions CI/CD pipelines.

A GitHub Actions workflow has FAILED. Below are the failure logs, followed by all relevant
source files from the repository.

## FAILURE LOGS
{logs}

## REPOSITORY SOURCE FILES
{file_context}

## YOUR TASK
1. Diagnose the ROOT CAUSE of the failure precisely.
2. Identify which files need to be changed to fix the issue.
3. Provide the FULL corrected content for each file that needs updating.
4. Return your answer ONLY as a single JSON block inside ```json ... ```.

## REQUIRED JSON FORMAT
```json
{{
  "diagnosis": "Detailed one-paragraph root cause explanation",
  "corrections": [
    {{
      "file_path": "relative/path/to/file",
      "corrected_content": "Full corrected file content here"
    }}
  ]
}}
```

Rules:
- file_path must be relative to the repo root (e.g. "Terraform/environment/dev/main.tf").
- corrected_content must be the COMPLETE file content, not a diff or partial snippet.
- If no file changes are needed (e.g. transient network error), return an empty corrections list.
- Do NOT include any text outside the ```json block.
"""

        print("\n[Pipeline Agent] Consulting Gemini for diagnosis and fix…")
        try:
            from llm_client import generate_text_with_retry
            raw = generate_text_with_retry(self.gemini_client, prompt)

            # Extract the JSON block
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()
            else:
                json_str = raw

            result = json.loads(json_str)
            print(f"\n  [Diagnosis] {result.get('diagnosis', 'N/A')[:300]}")
            corrections = result.get("corrections", [])
            print(f"  [Fixes] {len(corrections)} file(s) to update.")
            return result

        except json.JSONDecodeError as exc:
            print(f"  [ERROR] Failed to parse Gemini JSON response: {exc}")
            print(f"  Raw response (first 500 chars):\n{raw[:500]}")
            return None
        except Exception as exc:
            print(f"  [ERROR] Gemini call failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Step 5 — Apply file corrections to disk
    # ------------------------------------------------------------------

    def apply_corrections(self, corrections: list) -> int:
        """Write corrected file contents to disk. Returns count of files written."""
        written = 0
        for corr in corrections:
            file_path = corr.get("file_path", "").strip()
            content = corr.get("corrected_content", "")
            if not file_path:
                continue
            full_path = os.path.join(self.repo_root, file_path)
            print(f"  Applying fix → {file_path}")
            if self.dry_run:
                print(f"    [DRY RUN] Would overwrite {file_path}")
            else:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as fh:
                    fh.write(content)
                print(f"    ✓ Written {full_path}")
            written += 1
        return written

    # ------------------------------------------------------------------
    # Step 6 — Git commit + push fix branch
    # ------------------------------------------------------------------

    def commit_and_push(self, run_id: int, diagnosis: str) -> str | None:
        """
        Commit all changes, push to a unique fix branch, and return the branch name.
        Returns None if the push fails.
        """
        if self.dry_run:
            print("  [DRY RUN] Skipping git commit and push.")
            return f"fix/pipeline-run-{run_id}"

        branch = f"fix/pipeline-run-{run_id}"
        cwd = self.repo_root

        # Always start from main to avoid stacking fixes
        run_git(['checkout', 'main'], cwd=cwd)
        run_git(['pull', 'origin', 'main'], cwd=cwd)
        run_git(['checkout', '-B', branch], cwd=cwd)
        run_git(['add', '.'], cwd=cwd)

        commit_msg = (
            f"auto-fix: resolve pipeline failure for run #{run_id}\n\n"
            f"Diagnosis: {diagnosis[:500]}"
        )
        run_git(['commit', '-m', commit_msg], cwd=cwd)

        push = run_git(['push', '--force-with-lease', 'origin', branch], cwd=cwd)
        if push.returncode != 0:
            print(f"  [ERROR] Push failed:\n{push.stderr}")
            return None

        print(f"  ✓ Pushed fix branch '{branch}' to origin.")
        return branch

    # ------------------------------------------------------------------
    # Step 7 — Re-trigger the workflow run via GitHub API
    # ------------------------------------------------------------------

    def rerun_workflow(self, run_id: int) -> bool:
        """
        Ask GitHub to re-run all failed jobs in the given run via terminal gh CLI or API.
        """
        if self.dry_run:
            print(f"  [DRY RUN] Would re-trigger run #{run_id}.")
            return True

        print(f"\n[Pipeline Agent] Re-triggering run #{run_id} via terminal gh CLI / API…")
        
        # 1. Try terminal gh CLI
        try:
            res = subprocess.run(
                ["gh", "run", "rerun", str(run_id), "--failed", "--repo", self.repo],
                capture_output=True, text=True
            )
            if res.returncode == 0:
                print(f"  ✓ Re-run requested via terminal gh CLI for run #{run_id}.")
                return True
        except (FileNotFoundError, Exception):
            pass

        # 2. Fallback to API if token present
        if self.github_token:
            resp = self._gh_post(f"/actions/runs/{run_id}/rerun-failed-jobs")
            if resp and resp.status_code in (201, 204):
                print(f"  ✓ Re-run requested via API for run #{run_id}.")
                return True

        print(f"  [ERROR] Could not re-trigger run #{run_id}.")
        return False

    # ------------------------------------------------------------------
    # Step 8 — Open a PR (optional, after all retries exhausted)
    # ------------------------------------------------------------------

    def open_pull_request(self, branch: str, run_id: int, diagnosis: str):
        """Open a GitHub Pull Request from the fix branch into main via terminal gh CLI or API."""
        if self.dry_run or not branch:
            return

        title = f"🤖 Auto-Fix: Pipeline Failure in Run #{run_id}"
        body = (
            f"This PR was auto-generated by the **Pipeline Agent** to fix "
            f"failures in run #{run_id}.\n\n"
            f"**Diagnosis:**\n{diagnosis}\n\n"
            f"> Auto-fix applied — please review before merging."
        )

        # 1. Try terminal gh CLI
        try:
            res = subprocess.run(
                ["gh", "pr", "create", "--title", title, "--body", body,
                 "--head", branch, "--base", "main", "--repo", self.repo],
                capture_output=True, text=True
            )
            if res.returncode == 0:
                print(f"  ✓ Pull Request created via terminal gh CLI: {res.stdout.strip()}")
                return
        except (FileNotFoundError, Exception):
            pass

        # 2. Fallback to API if token present
        if self.github_token:
            url = f"https://api.github.com/repos/{self.repo}/pulls"
            data = {"title": title, "body": body, "head": branch, "base": "main"}
            resp = requests.post(url, headers=self.headers, json=data, timeout=30)
            if resp.status_code == 201:
                pr_url = resp.json().get("html_url")
                print(f"  ✓ Pull Request created via API: {pr_url}")
            elif resp.status_code == 422:
                print("  [INFO] PR already exists for this branch — skipping.")
            else:
                print(f"  [WARN] PR creation returned {resp.status_code}: {resp.text[:300]}")

    # ------------------------------------------------------------------
    # Main orchestration loop
    # ------------------------------------------------------------------

    def run(self):
        print("=" * 65)
        print("  Pipeline Agent — Auto-Monitor, Fix & Rerun")
        print(f"  Repository : {self.repo}")
        print(f"  Max Retries: {self.max_retries}")
        print(f"  Dry Run    : {self.dry_run}")
        print("=" * 65)

        # Get the latest run to start monitoring
        run = self.get_latest_run()
        if not run:
            print("[INFO] Nothing to monitor. Exiting.")
            return

        run_id = run["id"]

        # If still in progress, wait for it first
        if run.get("status") not in ("completed", "action_required", "cancelled", "timed_out"):
            run = self.wait_for_run(run_id)
            if not run:
                print("[ERROR] Could not determine run status. Exiting.")
                return

        # ---- Retry loop ----
        for attempt in range(1, self.max_retries + 1):
            conclusion = run.get("conclusion")
            run_id = run["id"]
            print(f"\n{'─'*65}")
            print(f"  Attempt {attempt}/{self.max_retries} | run_id={run_id} | conclusion={conclusion}")
            print(f"{'─'*65}")

            if conclusion == "success":
                print("\n✅ Pipeline PASSED — no intervention needed. Agent done.")
                return

            if conclusion != "failure":
                print(f"\n⚠️  Pipeline ended with conclusion='{conclusion}' — skipping auto-fix.")
                return

            # --- Pipeline failed: diagnose and fix ---
            print(f"\n❌ Pipeline FAILED on run #{run_id}.")
            logs = self.get_failure_logs(run_id)
            fix_result = self.diagnose_and_fix(logs)

            if not fix_result:
                print("[ERROR] Could not get a fix from Gemini. Stopping.")
                return

            diagnosis = fix_result.get("diagnosis", "")
            corrections = fix_result.get("corrections", [])

            if corrections:
                print(f"\n[Pipeline Agent] Applying {len(corrections)} correction(s)…")
                self.apply_corrections(corrections)
                branch = self.commit_and_push(run_id, diagnosis)
            else:
                print("\n[Pipeline Agent] No file changes suggested — attempting bare rerun…")
                branch = None

            # Re-trigger the failed run
            retriggered = self.rerun_workflow(run_id)

            if not retriggered:
                print("[ERROR] Could not re-trigger the workflow run. Stopping.")
                self.open_pull_request(branch, run_id, diagnosis)
                return

            # Small buffer before the re-triggered run appears in API
            time.sleep(15)

            # Fetch the newest run (the re-triggered one will be run_id+1 or appear as latest)
            latest = self.get_latest_run()
            if not latest:
                print("[ERROR] Could not find re-triggered run. Stopping.")
                return

            # If same run ID (GitHub reuses when rerun is on same run), wait for it
            new_run_id = latest["id"]
            run = self.wait_for_run(new_run_id)
            if not run:
                print("[ERROR] Timed out waiting for re-triggered run.")
                return

        # All retries exhausted
        print(f"\n⛔ Max retries ({self.max_retries}) reached. Pipeline still failing.")
        print("   Creating a Pull Request for human review…")
        if fix_result:
            self.open_pull_request(
                branch=branch,
                run_id=run_id,
                diagnosis=fix_result.get("diagnosis", "See attached logs."),
            )
        print("\nAgent finished.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Pipeline Agent — GitHub Actions Monitor, Auto-Fixer & Rerunner"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate all actions without writing files, committing, or calling GitHub APIs.",
    )
    args = parser.parse_args()

    agent = PipelineAgent(dry_run=args.dry_run)
    agent.run()
