"""
Deploy CLI — Natural-Language Single-Command Azure Deployer
===========================================================
The Master LLM Command Center. Type your intent in plain English and this tool
coordinates specialised AI agents to scaffold any software application, provision
infrastructure with Terraform, build and push containers to ACR, deploy to AKS,
and monitor GitHub Actions CI/CD with self-healing error recovery.

Usage examples:
  python ai_agents/deploy_cli.py "deploy a python fastapi microservice to azure dev"
  python ai_agents/deploy_cli.py "deploy a fullstack react and nodejs application to aks"
  python ai_agents/deploy_cli.py "deploy an nginx web application to dev"
  python ai_agents/deploy_cli.py "audit and provision terraform infrastructure in dev"
  python ai_agents/deploy_cli.py --app-dir ./my-app "deploy my existing application to azure"
  python ai_agents/deploy_cli.py --dry-run "deploy everything to prod"
  python ai_agents/deploy_cli.py --interactive   # interactive chat REPL mode
  python ai_agents/deploy_cli.py --web           # launch visual Web Command Center UI

How it works:
  1. Your natural-language intent is analyzed by Gemini LLM.
  2. Gemini decomposes it into an optimal multi-agent execution graph.
  3. App Agent scaffolds code, Dockerfile, and Kubernetes manifests for ANY tech stack.
  4. Terraform Agent audits and provisions Azure Landing Zone infrastructure.
  5. K8s/ACR Agent builds & pushes the container to ACR and rolls it out to AKS.
  6. Pipeline Agent oversees CI/CD workflows and self-heals any build/deploy errors.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# ── Bootstrap ───────────────────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

AGENTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = AGENTS_DIR.parent
load_dotenv(dotenv_path=AGENTS_DIR / '.env')

GEMINI_MODEL = "gemini-2.5-flash"

INTENT_SYSTEM_PROMPT = """
You are the Master Azure Landing Zone & Application Deployment Architect.
You translate any natural-language deployment instruction into an optimal, structured
execution plan for specialised AI agents in the `ai_agents` ecosystem.

## Available Specialised Agents:
1. `app_agent`:
   - Inspects existing application directory or SCAFFOLDS any new software application
     (FastAPI, Node.js/Express, React, Next.js, Vue, Go, Flask, Java Spring, Nginx, etc.)
   - Generates production-grade multi-stage Dockerfile (with healthcheck and non-root user)
   - Generates production Kubernetes manifests (Deployment, Service LoadBalancer, Ingress, HPA, ConfigMap)
2. `terraform_agent`:
   - Audits, fixes, plans, and deploys Azure Landing Zone infrastructure (VNet, Subnets, NSG, ACR, AKS, Storage, Resource Group)
3. `k8s_acr_agent`:
   - Builds container image via Azure Container Registry (`az acr build`), gets AKS credentials, applies manifests, and verifies pod rollout health with auto-rectify
4. `pipeline_agent`:
   - Monitors GitHub Actions CI/CD workflows, diagnoses failed jobs via Gemini, applies fixes, and re-triggers runs

## Available Environments:
- `dev` (default)
- `no-prod`
- `prod`

## JSON Schema:
```json
{
  "intent_summary": "One-sentence summary of the deployment goal",
  "app_spec": {
    "app_name": "kebab-case-name",
    "app_type": "fastapi|nodejs|react|golang|nginx|python|custom",
    "port": 80,
    "description": "App features and requirements"
  },
  "steps": [
    {
      "step": 1,
      "agent": "app_agent",
      "reason": "Scaffold application code, Dockerfile, and K8s manifests",
      "args": {
        "app_name": "app-name",
        "app_type": "fastapi",
        "app_description": "Detailed description of requested software application",
        "port": 8000,
        "namespace": "default",
        "dry_run": false
      }
    },
    {
      "step": 2,
      "agent": "terraform_agent",
      "reason": "Audit and provision Azure infrastructure for the target environment",
      "args": {
        "env": "dev",
        "audit_only": false,
        "max_retries": 3,
        "dry_run": false
      }
    },
    {
      "step": 3,
      "agent": "k8s_acr_agent",
      "reason": "Build & push container to ACR and deploy to AKS cluster",
      "args": {
        "skip_build": false,
        "skip_deploy": false,
        "max_retries": 3,
        "dry_run": false
      }
    }
  ],
  "warnings": ["Any relevant architectural assumptions or notes"]
}
```

## Planning Rules:
1. If the user mentions or implies deploying ANY software application (e.g. "deploy a FastAPI app", "deploy a web application", "deploy a React frontend", "deploy Node service", "deploy guestbook", etc.):
   - Step 1 MUST be `app_agent` to scaffold the app and generate Kubernetes manifests.
   - Step 2 should be `terraform_agent` (unless user explicitly said "skip infra" or "app only").
   - Step 3 should be `k8s_acr_agent` to build and deploy to AKS.
2. If the user asks for "infrastructure only", "audit terraform", or "provision landing zone":
   - Include only `terraform_agent`.
3. If the user mentions "CI/CD", "pipeline", "GitHub actions", or "test workflow":
   - Include `pipeline_agent`.
4. Default environment is "dev" unless specified otherwise.
5. Choose appropriate default ports:
   - FastAPI / Python / Uvicorn: 8000 or 80
   - Node.js / Express: 3000 or 80
   - React / Vite: 80 or 3000
   - Go / Gin: 8080 or 80
   - Nginx / Static: 80
   - Flask: 5000 or 80
   - Spring Boot: 8080 or 80
6. ONLY return the JSON block inside ```json ... ```. No conversational preamble.
"""


def get_client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("[ERROR] GEMINI_API_KEY not set in ai_agents/.env")
        sys.exit(1)
    return genai.Client(api_key=key)


def parse_intent(client: genai.Client, user_intent: str, dry_run: bool = False, custom_app_dir: str = None, target_env: str = None) -> dict:
    """Send user intent to Gemini and return a structured execution plan."""
    print(f"\n🧠 [Master LLM] Analyzing intent: \"{user_intent}\"…")
    
    context_notes = []
    if custom_app_dir:
        context_notes.append(f"- User specified custom app directory: {custom_app_dir}")
    if target_env:
        context_notes.append(f"- User explicitly specified target environment: {target_env}")

    extra_ctx = "\n".join(context_notes)
    prompt = f"{INTENT_SYSTEM_PROMPT}\n\n## User Intent\n{user_intent}\n\n{extra_ctx}"

    try:
        from llm_client import generate_text_with_retry
        raw = generate_text_with_retry(client, prompt)
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0].strip()
        else:
            json_str = raw
        plan = json.loads(json_str)

        # Propagate custom settings & dry_run flag
        for step in plan.get("steps", []):
            step_args = step.setdefault("args", {})
            if dry_run:
                step_args["dry_run"] = True
            if custom_app_dir and step.get("agent") == "app_agent":
                step_args["app_dir"] = custom_app_dir
            if target_env and step.get("agent") == "terraform_agent":
                step_args["env"] = target_env

        return plan
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Could not parse Gemini plan response: {exc}")
        print(f"  Raw response:\n{raw[:800]}")
        sys.exit(1)
    except Exception as exc:
        print(f"[ERROR] Gemini call failed: {exc}")
        sys.exit(1)


def display_plan(plan: dict):
    """Pretty-print the execution plan to the terminal."""
    print("\n" + "═" * 70)
    print(f"  📋  PLAN: {plan.get('intent_summary', 'Azure Deployment Plan')}")
    print("═" * 70)
    
    app_spec = plan.get("app_spec")
    if app_spec:
        print(f"  📦 Application Stack:")
        print(f"     • Name : {app_spec.get('app_name', 'N/A')}")
        print(f"     • Type : {app_spec.get('app_type', 'generic')}")
        print(f"     • Port : {app_spec.get('port', 80)}")
        if app_spec.get("description"):
            print(f"     • Info : {app_spec.get('description')}")
        print("─" * 70)

    steps = plan.get("steps", [])
    for step in steps:
        step_idx = step.get("step", "?")
        agent = step.get("agent", "?")
        reason = step.get("reason", "")
        args = step.get("args", {})
        print(f"  Step {step_idx}: [{agent.upper()}]")
        print(f"    • Purpose : {reason}")
        print(f"    • Config  : {json.dumps(args)}")
        print()

    warnings = plan.get("warnings", [])
    if warnings:
        print("  ⚠️  Architectural Notes & Warnings:")
        for w in warnings:
            print(f"    • {w}")
    print("═" * 70)


def confirm_execution(plan: dict, auto_yes: bool) -> bool:
    """Ask the user to confirm before running (skipped with --yes or --dry-run)."""
    if auto_yes:
        return True
    try:
        ans = input("\n▶  Execute this multi-agent plan on Azure? [y/N] ").strip().lower()
        return ans in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        return False


def run_plan(plan: dict):
    """Import and run the Orchestrator with the parsed plan."""
    try:
        sys.path.insert(0, str(AGENTS_DIR))
        from orchestrator import Orchestrator  # type: ignore
    except ImportError as exc:
        print(f"[ERROR] Could not import Orchestrator: {exc}")
        print("  Make sure ai_agents/orchestrator.py exists.")
        sys.exit(1)

    orch = Orchestrator()
    result = orch.execute_plan(plan)
    return result


def interactive_mode(client: genai.Client, dry_run: bool, auto_yes: bool):
    """REPL loop — interactive deployment command center."""
    print("\n" + "═" * 70)
    print("  🚀  Azure Autonomous Deployment Command Center (Interactive Mode)")
    print("  Type any deployment instruction in plain English.")
    print("  Examples:")
    print("    • deploy a fast-api microservice with redis to dev")
    print("    • deploy fullstack react and express app to azure")
    print("    • audit terraform code for prod")
    print("  Commands: 'quit' / 'exit' / 'help' / Ctrl+C")
    print("═" * 70)

    while True:
        try:
            intent = input("\n[Azure-AI] > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Command Center. Goodbye! 👋")
            break

        if not intent:
            continue
        if intent.lower() in ("quit", "exit", "q"):
            print("Exiting Command Center. Goodbye! 👋")
            break
        if intent.lower() == "help":
            print("  Type any command like 'deploy nodejs app to dev' or 'audit terraform dev'")
            continue

        plan = parse_intent(client, intent, dry_run)
        display_plan(plan)
        if confirm_execution(plan, auto_yes):
            run_plan(plan)
        else:
            print("  Execution skipped.")


def launch_web_ui(port: int = 5000):
    """Launch the sleek Web UI dashboard."""
    try:
        sys.path.insert(0, str(AGENTS_DIR))
        from web_ui import start_web_server  # type: ignore
        start_web_server(port=port)
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, str(AGENTS_DIR / "web_ui.py"), "--port", str(port)])


# ── Entry Point ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description=(
            "Azure Master LLM Deployer — Natural-Language Single-Command Deployment Engine.\n"
            "Deploys ANY software application and infrastructure to Azure with AI agents.\n\n"
            "Examples:\n"
            "  python deploy_cli.py \"deploy a python fastapi app to dev\"\n"
            "  python deploy_cli.py \"deploy a fullstack react and express app to aks\"\n"
            "  python deploy_cli.py --app-dir ./my-app \"deploy my app to azure\"\n"
            "  python deploy_cli.py --interactive\n"
            "  python deploy_cli.py --web"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "intent", nargs="?", default=None,
        help="Natural-language deployment intent (e.g. 'deploy a fastapi app to dev')"
    )
    parser.add_argument(
        "--app-dir", default=None,
        help="Path to custom existing application source directory"
    )
    parser.add_argument(
        "--env", choices=["dev", "no-prod", "prod"], default=None,
        help="Target environment override (dev, no-prod, prod)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate all actions — no real Azure/GitHub calls made"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompt and execute immediately"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Start an interactive chat REPL session"
    )
    parser.add_argument(
        "--web", "-w", action="store_true",
        help="Launch the visual Web Command Center dashboard"
    )
    parser.add_argument(
        "--port", type=int, default=5000,
        help="Port for Web UI server (default: 5000)"
    )
    parser.add_argument(
        "--show-plan-only", action="store_true",
        help="Parse and display the execution plan without running it"
    )
    args = parser.parse_args()

    if args.web:
        launch_web_ui(port=args.port)
        return

    if not args.intent and not args.interactive:
        parser.print_help()
        sys.exit(0)

    client = get_client()

    if args.interactive:
        interactive_mode(client, args.dry_run, args.yes)
        return

    # Single-shot mode
    plan = parse_intent(
        client=client,
        user_intent=args.intent,
        dry_run=args.dry_run,
        custom_app_dir=args.app_dir,
        target_env=args.env,
    )
    display_plan(plan)

    if args.show_plan_only:
        print("\n  [--show-plan-only] Execution skipped.")
        return

    if confirm_execution(plan, args.yes or args.dry_run):
        result = run_plan(plan)
        if result and result.get("success"):
            print("\n🎉 ✅ All deployment steps completed successfully!")
        else:
            print("\n⚠️   Some deployment steps encountered issues — check logs above.")
    else:
        print("\n  Execution cancelled by user.")


if __name__ == "__main__":
    main()
