"""
Deploy CLI — Natural-Language Single-Command Azure Deployer
===========================================================
The LLM Command Center. Type your intent in plain English and this tool
figures out which agents to run, in which order, and with what parameters.

Usage examples:
  python ai_agents/deploy_cli.py "deploy myapp to dev"
  python ai_agents/deploy_cli.py "audit terraform for prod"
  python ai_agents/deploy_cli.py "build and push docker image to acr"
  python ai_agents/deploy_cli.py "run full pipeline check and fix any errors"
  python ai_agents/deploy_cli.py "deploy infrastructure and app to no-prod"
  python ai_agents/deploy_cli.py --dry-run "deploy everything to dev"
  python ai_agents/deploy_cli.py --interactive   # chat-style REPL mode

How it works:
  1. Your natural-language intent is sent to Gemini.
  2. Gemini returns a structured JSON execution plan.
  3. The Orchestrator executes each step, passing context between agents.
  4. A final summary is printed to your terminal.

Environment (ai_agents/.env):
  All variables from .env.example are used — no extra setup needed.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# ── Bootstrap ───────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=Path(__file__).parent / '.env')

GEMINI_MODEL = "gemini-2.5-flash"
AGENTS_DIR = Path(__file__).parent

INTENT_SYSTEM_PROMPT = """
You are the Azure Landing Zone Deployment Planner — an AI that translates natural-language
deployment instructions into a structured execution plan for a set of specialised agents.

## Available Agents
| agent_id         | Description                                                        |
|------------------|--------------------------------------------------------------------|
| pipeline_agent   | Monitor GitHub Actions pipeline, fix failures, re-trigger runs     |
| terraform_agent  | Audit Terraform code, apply fixes, deploy infrastructure to Azure  |
| k8s_acr_agent    | Build/push Docker image to ACR, deploy app to AKS via kubectl      |

## Available Environments
dev, no-prod, prod

## Your Task
Parse the user's intent and return ONLY a JSON execution plan inside ```json ... ```.

## JSON Schema
```json
{
  "intent_summary": "One-sentence summary of what the user wants",
  "steps": [
    {
      "step": 1,
      "agent": "<agent_id>",
      "reason": "Why this step is needed",
      "args": {
        "env": "dev",              // terraform_agent only: dev | no-prod | prod
        "audit_only": false,       // terraform_agent: true = audit without deploy
        "max_retries": 3,
        "dry_run": false,
        "skip_build": false,       // k8s_acr_agent: skip ACR build
        "skip_deploy": false       // k8s_acr_agent: skip K8s deploy
      }
    }
  ],
  "warnings": ["Any warnings or assumptions the user should know about"]
}
```

## Rules
- Order steps so infrastructure (terraform_agent) comes before app deploy (k8s_acr_agent).
- pipeline_agent should only appear if the user mentions pipeline, CI/CD, GitHub Actions, or workflow.
- If the user says "everything" or "full deploy", include all three agents in order.
- If the user says "audit only" or "check", set audit_only=true and skip k8s_acr_agent.
- Default environment is "dev" unless the user specifies otherwise.
- ONLY return the JSON block — no other text.
"""


def get_client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("[ERROR] GEMINI_API_KEY not set in ai_agents/.env")
        sys.exit(1)
    return genai.Client(api_key=key)


def parse_intent(client: genai.Client, user_intent: str, dry_run: bool) -> dict:
    """Send user intent to Gemini and return a structured execution plan."""
    print(f"\n🧠 Thinking about: \"{user_intent}\"")
    prompt = f"{INTENT_SYSTEM_PROMPT}\n\n## User Intent\n{user_intent}"

    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        raw = resp.text.strip()
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0].strip()
        else:
            json_str = raw
        plan = json.loads(json_str)
        # Propagate global dry_run flag
        if dry_run:
            for step in plan.get("steps", []):
                step.setdefault("args", {})["dry_run"] = True
        return plan
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Could not parse Gemini plan response: {exc}")
        print(f"  Raw:\n{raw[:800]}")
        sys.exit(1)
    except Exception as exc:
        print(f"[ERROR] Gemini call failed: {exc}")
        sys.exit(1)


def display_plan(plan: dict):
    """Pretty-print the execution plan to the terminal."""
    print("\n" + "═" * 65)
    print(f"  📋  {plan.get('intent_summary', 'Execution Plan')}")
    print("═" * 65)
    for step in plan.get("steps", []):
        agent = step.get("agent", "?")
        reason = step.get("reason", "")
        args = step.get("args", {})
        print(f"\n  Step {step.get('step', '?')}: [{agent}]")
        print(f"    Reason : {reason}")
        print(f"    Config : {json.dumps(args, indent=None)}")
    warnings = plan.get("warnings", [])
    if warnings:
        print("\n  ⚠️  Warnings:")
        for w in warnings:
            print(f"    • {w}")
    print("═" * 65)


def confirm_execution(plan: dict, auto_yes: bool) -> bool:
    """Ask the user to confirm before running (skipped with --yes or --dry-run)."""
    if auto_yes:
        return True
    try:
        ans = input("\n▶  Proceed with this plan? [y/N] ").strip().lower()
        return ans in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        return False


def run_plan(plan: dict):
    """Import and run the Orchestrator with the parsed plan."""
    # Import here to avoid circular imports and allow deploy_cli.py to be
    # used standalone (without orchestrator installed).
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
    """REPL loop — keep accepting commands until the user quits."""
    print("\n" + "═" * 65)
    print("  🚀  Azure Deploy CLI — Interactive Mode")
    print("  Type your deployment intent in plain English.")
    print("  Commands: 'quit' / 'exit' / Ctrl+C to stop.")
    print("═" * 65)

    while True:
        try:
            intent = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye! 👋")
            break

        if not intent:
            continue
        if intent.lower() in ("quit", "exit", "q"):
            print("Goodbye! 👋")
            break

        plan = parse_intent(client, intent, dry_run)
        display_plan(plan)
        if confirm_execution(plan, auto_yes):
            run_plan(plan)
        else:
            print("  Skipped.")


# ── Entry Point ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description=(
            "Azure Deploy CLI — Natural-language single-command deployer.\n"
            "Examples:\n"
            "  python deploy_cli.py \"deploy myapp to dev\"\n"
            "  python deploy_cli.py --dry-run \"full deploy to prod\"\n"
            "  python deploy_cli.py --interactive"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "intent", nargs="?", default=None,
        help="Natural-language deployment intent (e.g. 'deploy myapp to dev')"
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
        help="Start an interactive REPL session"
    )
    parser.add_argument(
        "--show-plan-only", action="store_true",
        help="Parse and display the execution plan without running it"
    )
    args = parser.parse_args()

    if not args.intent and not args.interactive:
        parser.print_help()
        sys.exit(0)

    client = get_client()

    if args.interactive:
        interactive_mode(client, args.dry_run, args.yes)
        return

    # Single-shot mode
    plan = parse_intent(client, args.intent, args.dry_run)
    display_plan(plan)

    if args.show_plan_only:
        print("\n  [--show-plan-only] Not executing.")
        return

    if confirm_execution(plan, args.yes or args.dry_run):
        result = run_plan(plan)
        if result and result.get("success"):
            print("\n✅  All steps completed successfully!")
        else:
            print("\n⚠️   Some steps may have encountered issues — check logs above.")
    else:
        print("\n  Execution cancelled by user.")


if __name__ == "__main__":
    main()
