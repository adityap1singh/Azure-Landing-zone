"""
Terraform Agent — Audit, Auto-Fix & Deploy with Error-Rectify-Rerun Loop
=========================================================================
Responsibilities:
  1. AUDIT  — Walk all .tf files under Terraform/, send each to Gemini for a
              structured code review (PASS / WARNING / FAIL + remediation hints).
  2. AUTO-FIX — For any file rated WARNING or FAIL, ask Gemini for the full
                corrected content and write it back to disk.
  3. DEPLOY  — Run `terraform init → plan → apply` in the target environment
               directory via subprocess.
  4. ERROR-RECTIFY-RERUN — If `terraform apply` fails, capture stderr, ask
               Gemini to produce corrected files, write them, then re-run
               `terraform apply` — up to MAX_RETRIES times.

Usage:
  python terraform_agent.py [--env dev|no-prod|prod] [--dry-run] [--audit-only]

Environment variables (ai_agents/.env):
  GEMINI_API_KEY         — Google Gemini API key
  AZURE_SUBSCRIPTION_ID  — Target Azure subscription
  AZURE_CLIENT_ID        — Service Principal client ID
  AZURE_CLIENT_SECRET    — Service Principal client secret
  AZURE_TENANT_ID        — Azure tenant ID
  TF_MAX_RETRIES         — Max deploy-rectify cycles (default: 3)
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_MAX_RETRIES = int(os.getenv("TF_MAX_RETRIES", "3"))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent   # …/Azure-Landing-zone/
TF_ROOT = REPO_ROOT / "Terraform"
ENV_DIR_MAP = {
    "dev":     TF_ROOT / "environment" / "dev",
    "no-prod": TF_ROOT / "environment" / "no-prod",
    "prod":    TF_ROOT / "environment" / "prod",
}


def get_env(name: str, default=None, required=False) -> str:
    val = os.getenv(name, default)
    if required and not val:
        print(f"[ERROR] Required environment variable '{name}' is not set.")
        sys.exit(1)
    return val


def get_gemini_client() -> genai.Client:
    api_key = get_env("GEMINI_API_KEY", required=True)
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def find_tf_files(search_root: Path) -> list[Path]:
    """Return all .tf files under search_root, skipping hidden directories."""
    tf_files = []
    for path in search_root.rglob("*.tf"):
        if any(part.startswith('.') for part in path.parts):
            continue
        tf_files.append(path)
    return sorted(tf_files)


def run_terraform(args: list[str], cwd: Path, dry_run: bool = False) -> tuple[int, str, str]:
    """
    Run a terraform sub-command and return (returncode, stdout, stderr).
    In dry_run mode, prints the command but does not execute it.
    """
    cmd = ["terraform"] + args
    print(f"  [terraform] {' '.join(cmd)}")
    if dry_run:
        print("    [DRY RUN] Skipping actual execution.")
        return 0, "[DRY RUN]", ""
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout[-3000:])   # last 3 000 chars to keep output sane
    if result.stderr:
        print(result.stderr[-2000:])
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# PHASE 1 — Audit
# ---------------------------------------------------------------------------

def audit_tf_file(path: Path, client: genai.Client) -> dict:
    """
    Ask Gemini to review a single Terraform file.
    Returns a dict with keys: file, status, issues, recommendations, raw.
    """
    try:
        code = path.read_text(encoding='utf-8', errors='replace')
    except Exception as exc:
        return {"file": str(path), "status": "ERROR", "issues": [str(exc)], "raw": ""}

    prompt = f"""You are an Azure Landing Zone Terraform Security and Compliance Reviewer.
Analyse the following Terraform file for:
- Security misconfigurations (open NSGs, public IPs without justification, missing encryption, etc.)
- Azure best-practice violations (naming conventions, tagging, resource locks)
- Syntax or logic errors that would cause `terraform validate` or `terraform apply` to fail
- Cost optimisation opportunities

File: {path.relative_to(REPO_ROOT)}

```hcl
{code}
```

Respond ONLY with a JSON object inside ```json ... ```:
```json
{{
  "status": "PASS" | "WARNING" | "FAIL",
  "issues": ["issue 1", "issue 2"],
  "recommendations": ["fix 1", "fix 2"],
  "corrected_content": "Full corrected HCL if status is WARNING or FAIL, else empty string"
}}
```
"""
    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        raw = resp.text.strip()
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0].strip()
        else:
            json_str = raw
        data = json.loads(json_str)
        data["file"] = str(path)
        data["raw"] = raw
        return data
    except Exception as exc:
        return {
            "file": str(path),
            "status": "ERROR",
            "issues": [f"Gemini call failed: {exc}"],
            "recommendations": [],
            "corrected_content": "",
            "raw": "",
        }


def run_audit(dry_run: bool, client: genai.Client) -> list[dict]:
    """Audit all Terraform files and return the list of audit results."""
    print("\n" + "="*65)
    print("  PHASE 1 — Terraform Code Audit")
    print("="*65)

    tf_files = find_tf_files(TF_ROOT)
    if not tf_files:
        print(f"  [WARN] No .tf files found under {TF_ROOT}")
        return []

    print(f"  Found {len(tf_files)} Terraform file(s) to audit.\n")
    results = []
    for tf_path in tf_files:
        rel = tf_path.relative_to(REPO_ROOT)
        print(f"  Auditing: {rel} …", end=" ", flush=True)
        result = audit_tf_file(tf_path, client)
        status = result.get("status", "ERROR")
        print(status)

        issues = result.get("issues", [])
        for issue in issues:
            print(f"    ⚠ {issue}")
        results.append(result)

    # Summary
    counts = {"PASS": 0, "WARNING": 0, "FAIL": 0, "ERROR": 0}
    for r in results:
        counts[r.get("status", "ERROR")] = counts.get(r.get("status", "ERROR"), 0) + 1
    print(f"\n  Audit Summary: PASS={counts['PASS']} | WARNING={counts['WARNING']}"
          f" | FAIL={counts['FAIL']} | ERROR={counts['ERROR']}")
    return results


# ---------------------------------------------------------------------------
# PHASE 2 — Auto-Fix
# ---------------------------------------------------------------------------

def apply_audit_fixes(audit_results: list[dict], dry_run: bool) -> int:
    """Write corrected content for WARNING/FAIL files. Returns count fixed."""
    print("\n" + "="*65)
    print("  PHASE 2 — Auto-Fix Identified Issues")
    print("="*65)

    fixed = 0
    for result in audit_results:
        if result.get("status") not in ("WARNING", "FAIL"):
            continue
        corrected = result.get("corrected_content", "").strip()
        if not corrected:
            print(f"  [SKIP] No corrected content provided for: {result['file']}")
            continue
        file_path = Path(result["file"])
        print(f"  Fixing: {file_path.relative_to(REPO_ROOT)}")
        if dry_run:
            print("    [DRY RUN] Would overwrite file.")
        else:
            file_path.write_text(corrected, encoding='utf-8')
            print(f"    ✓ Updated {file_path.name}")
        fixed += 1
    print(f"\n  {fixed} file(s) updated by auto-fix.")
    return fixed


# ---------------------------------------------------------------------------
# PHASE 3 + 4 — Deploy + Error-Rectify-Rerun
# ---------------------------------------------------------------------------

def build_deploy_fix_prompt(error_output: str, env_dir: Path) -> str:
    """Build a Gemini prompt that includes all tf files + the Terraform error."""
    tf_files = find_tf_files(TF_ROOT)
    file_context = ""
    for tf_path in tf_files:
        try:
            code = tf_path.read_text(encoding='utf-8', errors='replace')
        except Exception:
            code = "[unreadable]"
        rel = tf_path.relative_to(REPO_ROOT)
        file_context += f"\n--- FILE: {rel} ---\n{code}\n"

    return f"""You are an Azure Terraform DevOps engineer.
The command `terraform apply` failed with the following error output.
Your job is to identify which Terraform file(s) need to be changed to fix the error
and provide their COMPLETE corrected content.

## TERRAFORM ERROR OUTPUT
{error_output}

## CURRENT TERRAFORM FILES
{file_context}

## TARGET ENVIRONMENT DIRECTORY
{env_dir.relative_to(REPO_ROOT)}

Respond ONLY with a single JSON block inside ```json ... ```:
```json
{{
  "diagnosis": "Root cause explanation",
  "corrections": [
    {{
      "file_path": "relative/path/from/repo/root/to/file.tf",
      "corrected_content": "Full corrected HCL content"
    }}
  ]
}}
```

Rules:
- file_path is RELATIVE to the repository root.
- corrected_content is the FULL file content (not a diff).
- If the error is transient (e.g. Azure API throttle), set corrections to [].
"""


def apply_deploy_corrections(corrections: list[dict], dry_run: bool) -> int:
    """Write Gemini-suggested corrections to disk. Returns count written."""
    written = 0
    for corr in corrections:
        rel_path = corr.get("file_path", "").strip()
        content = corr.get("corrected_content", "")
        if not rel_path or not content:
            continue
        full_path = REPO_ROOT / rel_path
        print(f"  Applying fix → {rel_path}")
        if dry_run:
            print("    [DRY RUN] Would overwrite.")
        else:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
            print(f"    ✓ Written {full_path.name}")
        written += 1
    return written


def run_deploy(env: str, dry_run: bool, client: genai.Client, max_retries: int):
    """Run terraform init → plan → apply with error-rectify-rerun loop."""
    print("\n" + "="*65)
    print(f"  PHASE 3 — Terraform Deploy  [env={env}]")
    print("="*65)

    env_dir = ENV_DIR_MAP.get(env)
    if not env_dir:
        print(f"  [ERROR] Unknown environment '{env}'. Valid: {list(ENV_DIR_MAP.keys())}")
        sys.exit(1)
    if not env_dir.exists():
        print(f"  [ERROR] Environment directory not found: {env_dir}")
        sys.exit(1)

    print(f"  Working directory: {env_dir}")

    # --- terraform init (once, not retried) ---
    rc, _, stderr = run_terraform(["init", "-input=false"], env_dir, dry_run)
    if rc != 0:
        print(f"  [ERROR] terraform init failed — cannot proceed.\n{stderr}")
        sys.exit(1)

    # --- terraform plan ---
    rc, _, stderr = run_terraform(["plan", "-out=tfplan", "-input=false"], env_dir, dry_run)
    if rc != 0:
        print(f"  [ERROR] terraform plan failed.\n{stderr}")
        # We still attempt apply in the loop below — plan failure usually means code issues
        # that Gemini can fix.

    # --- terraform apply loop ---
    for attempt in range(1, max_retries + 1):
        print(f"\n{'─'*65}")
        print(f"  Deploy Attempt {attempt}/{max_retries}")
        print(f"{'─'*65}")

        rc, stdout, stderr = run_terraform(
            ["apply", "-auto-approve", "-input=false", "tfplan"],
            env_dir, dry_run
        )

        if rc == 0:
            print("\n✅ terraform apply SUCCEEDED!")
            return True

        # --- Apply failed — call Gemini to rectify ---
        print(f"\n❌ terraform apply FAILED (exit code {rc}).")
        error_text = f"STDOUT:\n{stdout[-2000:]}\n\nSTDERR:\n{stderr[-2000:]}"

        print("\n[Terraform Agent] Consulting Gemini for error rectification…")
        prompt = build_deploy_fix_prompt(error_text, env_dir)
        try:
            resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            raw = resp.text.strip()
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()
            else:
                json_str = raw
            fix_data = json.loads(json_str)
            diagnosis = fix_data.get("diagnosis", "")
            corrections = fix_data.get("corrections", [])
            print(f"  Diagnosis: {diagnosis[:300]}")
            print(f"  Corrections: {len(corrections)} file(s)")
        except Exception as exc:
            print(f"  [ERROR] Gemini rectification call failed: {exc}")
            corrections = []

        if corrections:
            apply_deploy_corrections(corrections, dry_run)
            # Re-plan after fixes
            print("\n  Re-running terraform plan after fixes…")
            run_terraform(["plan", "-out=tfplan", "-input=false"], env_dir, dry_run)
        else:
            print("  [INFO] No corrections — retrying apply as-is (may be transient error).")

    print(f"\n⛔ Max deploy retries ({max_retries}) exhausted. Infrastructure may be partially deployed.")
    print("   Review the Azure portal and Terraform state for partial resources.")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Terraform Agent — Audit, Auto-Fix, Deploy & Error-Rectify"
    )
    parser.add_argument(
        "--env", choices=["dev", "no-prod", "prod"], default="dev",
        help="Target environment (default: dev)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate all actions without writing files or running terraform"
    )
    parser.add_argument(
        "--audit-only", action="store_true",
        help="Run audit and auto-fix only — skip terraform deploy"
    )
    parser.add_argument(
        "--max-retries", type=int, default=DEFAULT_MAX_RETRIES,
        help=f"Max deploy-rectify attempts (default: {DEFAULT_MAX_RETRIES})"
    )
    args = parser.parse_args()

    print("=" * 65)
    print("  Terraform Agent — Audit + Deploy + Auto-Fix")
    print(f"  Environment : {args.env}")
    print(f"  Dry Run     : {args.dry_run}")
    print(f"  Audit Only  : {args.audit_only}")
    print(f"  Max Retries : {args.max_retries}")
    print("=" * 65)

    client = get_gemini_client()

    # Phase 1 — Audit
    audit_results = run_audit(args.dry_run, client)

    # Phase 2 — Auto-Fix
    apply_audit_fixes(audit_results, args.dry_run)

    # Phase 3+4 — Deploy + Error-Rectify-Rerun
    if not args.audit_only:
        run_deploy(args.env, args.dry_run, client, args.max_retries)
    else:
        print("\n[INFO] --audit-only flag set. Skipping deploy.")

    print("\n[Terraform Agent] Done.")


if __name__ == "__main__":
    main()
