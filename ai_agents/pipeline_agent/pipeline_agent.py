import os
import sys
import subprocess
import json
import requests
from google import genai
from dotenv import load_dotenv

# Load env variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

def get_env_variable(name, default=None, required=False):
    val = os.getenv(name, default)
    if required and not val:
        print(f"Error: Required environment variable '{name}' is missing.")
        sys.exit(1)
    return val

def run_git_cmd(args):
    print(f"Running git command: {' '.join(args)}")
    res = subprocess.run(['git'] + args, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Git command failed: {res.stderr.strip()}")
    return res

class PipelineAgent:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.github_token = get_env_variable("GITHUB_TOKEN")
        self.repo = get_env_variable("GITHUB_REPOSITORY") # Format: owner/repo
        self.gemini_client = genai.Client(api_key=get_env_variable("GEMINI_API_KEY"))
        
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.github_token}" if self.github_token else ""
        }
        
    def check_pipeline_status(self):
        if not self.repo:
            print("Error: GITHUB_REPOSITORY environment variable not set. E.g., 'my-org/my-repo'")
            return None
            
        url = f"https://api.github.com/repos/{self.repo}/actions/runs"
        print(f"Checking latest workflow runs for {self.repo}...")
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"Failed to fetch runs: {response.status_code} - {response.text}")
                return None
            
            runs = response.json().get("workflow_runs", [])
            if not runs:
                print("No workflow runs found.")
                return None
                
            latest_run = runs[0]
            print(f"Latest Run: #{latest_run.get('run_number')} ({latest_run.get('name')})")
            print(f"Status: {latest_run.get('status')}, Conclusion: {latest_run.get('conclusion')}")
            return latest_run
        except Exception as e:
            print(f"Error checking pipeline: {str(e)}")
            return None

    def get_failed_job_logs(self, run_id):
        url = f"https://api.github.com/repos/{self.repo}/actions/runs/{run_id}/jobs"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                return f"Could not fetch jobs: {response.text}"
                
            jobs = response.json().get("jobs", [])
            logs_summary = []
            
            for job in jobs:
                if job.get("conclusion") == "failure":
                    job_id = job.get("id")
                    job_name = job.get("name")
                    print(f"Failed job identified: {job_name} (ID: {job_id})")
                    
                    # Fetch logs for the job
                    log_url = f"https://api.github.com/repos/{self.repo}/actions/jobs/{job_id}/logs"
                    log_res = requests.get(log_url, headers=self.headers)
                    if log_res.status_code == 200:
                        # Truncate log to last 1500 lines to fit prompt easily
                        lines = log_res.text.splitlines()
                        truncated_log = "\n".join(lines[-1500:])
                        logs_summary.append(f"Job: {job_name}\nLogs:\n{truncated_log}")
                    else:
                        logs_summary.append(f"Job: {job_name} (Logs could not be fetched: {log_res.status_code})")
            return "\n\n".join(logs_summary)
        except Exception as e:
            return f"Error retrieving logs: {str(e)}"

    def suggest_and_apply_fix(self, logs):
        # We find files in the repo to provide context or let the LLM analyze it.
        # Let's locate tf files.
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        tf_files_content = {}
        tf_root = os.path.join(repo_root, "Terraform")
        
        if os.path.exists(tf_root):
            for root, _, files in os.walk(tf_root):
                for file in files:
                    if file.endswith('.tf'):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, repo_root)
                        with open(full_path, 'r', encoding='utf-8') as f:
                            tf_files_content[rel_path] = f.read()
                            
        files_context = "\n".join([f"--- File: {path} ---\n{content}" for path, content in tf_files_content.items()])

        prompt = f"""
You are an expert DevOps engineer and a Terraform/CI-CD troubleshooter.
The GitHub workflow has failed. Here are the logs:
{logs}

Here are the related Terraform files in the repository:
{files_context}

Please:
1. Diagnose the root cause of the error.
2. Provide the corrected content of the files that need to be updated.
3. You must output the response in a JSON-parseable format. Keep the format exactly as:
{{
  "diagnosis": "Detailed description of the issue",
  "corrections": [
     {{
       "file_path": "relative/path/to/file.tf",
       "corrected_content": "Full corrected content of the file"
     }}
  ]
}}
Ensure the JSON is correct, does not contain trailing commas, and is enclosed inside ```json ``` block.
"""
        print("Consulting Gemini for pipeline correction...")
        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
            )
            raw_text = response.text.strip()
            
            # Extract JSON block
            if "```json" in raw_text:
                json_part = raw_text.split("```json")[1].split("```")[0].strip()
            else:
                json_part = raw_text
                
            result = json.loads(json_part)
            print(f"Diagnosis: {result.get('diagnosis')}")
            
            for corr in result.get('corrections', []):
                file_path = corr.get('file_path')
                content = corr.get('corrected_content')
                full_path = os.path.join(repo_root, file_path)
                
                print(f"Applying fix to {file_path}...")
                if not self.dry_run:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Successfully updated {file_path}")
                else:
                    print(f"[DRY RUN] Would write to {file_path}")
            return result
        except Exception as e:
            print(f"Failed to parse or apply fix: {str(e)}")
            return None

    def git_push_and_pr(self, run_id, diagnosis):
        if self.dry_run:
            print("[DRY RUN] Skipping git commit, push, and PR creation.")
            return
            
        branch_name = f"fix/pipeline-run-{run_id}"
        run_git_cmd(['checkout', '-b', branch_name])
        run_git_cmd(['add', '.'])
        run_git_cmd(['commit', '-m', f"auto-fix: resolve pipeline failures for run #{run_id}"])
        
        print(f"Pushing branch {branch_name} to remote...")
        push_res = run_git_cmd(['push', 'origin', branch_name])
        if push_res.returncode != 0:
            print("Failed to push changes.")
            return
            
        # Raise PR via GitHub API
        url = f"https://api.github.com/repos/{self.repo}/pulls"
        data = {
            "title": f"Auto-Fix: Pipeline Failures Run #{run_id}",
            "body": f"This PR was auto-generated by the Pipeline Corrector Agent to fix failures in run #{run_id}.\n\n**Diagnosis:**\n{diagnosis}",
            "head": branch_name,
            "base": "main"
        }
        
        print("Creating Pull Request...")
        pr_res = requests.post(url, headers=self.headers, json=data)
        if pr_res.status_code == 201:
            pr_data = pr_res.json()
            print(f"Successfully raised PR: {pr_data.get('html_url')}")
        else:
            print(f"Failed to raise PR: {pr_res.status_code} - {pr_res.text}")

    def run(self):
        latest_run = self.check_pipeline_status()
        if not latest_run:
            return
            
        conclusion = latest_run.get("conclusion")
        run_id = latest_run.get("id")
        
        if conclusion == "failure":
            print(f"Pipeline failure detected for run #{run_id}!")
            logs = self.get_failed_job_logs(run_id)
            fix_result = self.suggest_and_apply_fix(logs)
            if fix_result:
                self.git_push_and_pr(run_id, fix_result.get('diagnosis'))
        else:
            print("Latest pipeline run did not fail. No corrections needed.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Pipeline Monitor and Auto-Corrector Agent")
    parser.add_argument("--dry-run", action="store_true", help="Run without applying changes or pushing to git")
    args = parser.parse_args()
    
    agent = PipelineAgent(dry_run=args.dry_run)
    agent.run()
