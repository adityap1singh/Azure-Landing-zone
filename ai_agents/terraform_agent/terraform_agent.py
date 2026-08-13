import os
from google import genai
from dotenv import load_dotenv

# Load env variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found in environment or .env file.")
        print("Using system defaults or hoping for active environment credentials.")
    return genai.Client()

def find_terraform_files(repo_root):
    tf_files = []
    # We want to check under the Terraform folder specifically
    tf_root = os.path.join(repo_root, "Terraform")
    if not os.path.exists(tf_root):
        # Fallback to repo root if Terraform folder not found
        tf_root = repo_root
        
    for root, dirs, files in os.walk(tf_root):
        # Ignore common directories
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue
        for file in files:
            if file.endswith('.tf'):
                tf_files.append(os.path.join(root, file))
    return tf_files

def analyze_terraform_code(file_path, client):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

    prompt = f"""
You are a Cloud Infrastructure Architect and a Terraform Code Review Agent.
Analyze the following Terraform file for security flaws, configuration issues, resource naming best practices, syntax concerns, or general improvements under Azure Landing Zone guidelines.

File Path: {file_path}

Terraform Code:
```hcl
{code}
```

Provide your analysis in a structured format:
1. **Status**: PASS / WARNING / FAIL
2. **Issues Found**: Bullet points detailing any concerns.
3. **Recommended Fixes**: Specific code snippet suggestions for remediation.
"""
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"Error generating analysis: {str(e)}"

def run_agent():
    print("=== Terraform Code Quality Checker Agent ===")
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f"Scanning for Terraform files in: {repo_root}")
    
    tf_files = find_terraform_files(repo_root)
    if not tf_files:
        print("No Terraform (.tf) files found.")
        return
        
    print(f"Found {len(tf_files)} Terraform files to inspect.")
    client = get_gemini_client()
    
    for tf_file in tf_files:
        rel_path = os.path.relpath(tf_file, repo_root)
        print(f"\nAnalyzing: {rel_path}...")
        report = analyze_terraform_code(tf_file, client)
        print(f"\n--- Analysis Report for {rel_path} ---")
        print(report)
        print("="*60)

if __name__ == "__main__":
    run_agent()
