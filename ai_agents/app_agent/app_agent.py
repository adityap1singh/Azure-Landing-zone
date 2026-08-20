"""
App Agent — Application Inspector, Scaffolder & Kubernetes Manifest Generator
=============================================================================
Responsibilities:
  1. INSPECT   — Analyse an existing app directory (detect language/framework,
                 dependencies, entrypoint, port, Dockerfile).
  2. SCAFFOLD  — If deploying a new application (e.g. FastAPI, Node.js Express,
                 React, Go, Nginx, Flask, etc.) or app doesn't exist, ask
                 Gemini to generate a complete, production-grade application
                 source codebase, dependencies, and health endpoints.
  3. DOCKERIZE — Generate an enterprise, multi-stage Dockerfile with non-root
                 security, optimal layer caching, and healthchecks.
  4. MANIFESTS — Generate production-grade Kubernetes manifests (Deployment,
                 Service, Ingress, HPA, ConfigMap) tailored to the app.
  5. SELF-HEAL — If build/deploy issues arise, diagnose and rewrite manifests
                 or source code.

Usage (CLI):
  python app_agent.py --app-name fast-api-service --app-type fastapi --port 8000
  python app_agent.py --inspect ./my-existing-app
  python app_agent.py --app-name webapp --prompt "React frontend with Node backend"
"""

import os
import sys
import json
import argparse
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# ── Bootstrap ─────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

AGENTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = AGENTS_DIR.parent
load_dotenv(dotenv_path=AGENTS_DIR / '.env')
sys.path.insert(0, str(AGENTS_DIR))

try:
    from llm_client import get_gemini_client, generate_text_with_retry
except ImportError:
    def get_gemini_client():
        return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    def generate_text_with_retry(client, prompt):
        return client.models.generate_content(model="gemini-2.5-flash", contents=prompt).text.strip()


class AppScaffolder:
    """
    Scaffolds, dockerizes, and generates Kubernetes manifests for ANY software application.
    """

    def __init__(self, client: genai.Client = None, dry_run: bool = False):
        self.client = client or get_gemini_client()
        self.dry_run = dry_run

    def inspect_directory(self, app_dir: Path) -> dict:
        """
        Inspect an existing app directory to detect its technology stack,
        port, Dockerfile presence, and Kubernetes manifests.
        """
        print(f"\n🔍 [App Agent] Inspecting directory: {app_dir}")
        if not app_dir.exists():
            return {"exists": False, "files": []}

        files = [p.relative_to(app_dir).as_posix() for p in app_dir.rglob("*") if p.is_file()]
        
        has_dockerfile = any(f.lower() in ("dockerfile", "dockerfile.prod") for f in files)
        has_package_json = "package.json" in files
        has_requirements_txt = "requirements.txt" in files or "pyproject.toml" in files
        has_go_mod = "go.mod" in files
        has_pom_xml = "pom.xml" in files or "build.gradle" in files
        
        detected_type = "generic"
        if has_package_json:
            detected_type = "nodejs"
        elif has_requirements_txt:
            detected_type = "python"
        elif has_go_mod:
            detected_type = "golang"
        elif has_pom_xml:
            detected_type = "java"
        elif any(f.endswith(".html") for f in files):
            detected_type = "static_html"

        return {
            "exists": True,
            "detected_type": detected_type,
            "has_dockerfile": has_dockerfile,
            "total_files": len(files),
            "sample_files": files[:15],
        }

    def scaffold_application(
        self,
        app_name: str,
        app_type: str = "fastapi",
        description: str = "",
        target_dir: Path = None,
        port: int = 80,
    ) -> dict:
        """
        Generate full application source code, Dockerfile, and metadata via Gemini.
        """
        if not target_dir:
            target_dir = REPO_ROOT / "apps" / app_name

        print(f"\n🚀 [App Agent] Scaffolding application '{app_name}' ({app_type}) in {target_dir.relative_to(REPO_ROOT) if target_dir.is_relative_to(REPO_ROOT) else target_dir}…")

        prompt = f"""You are a Principal Software Architect and DevOps Engineer.
Generate a complete, modern, production-ready software application codebase.

APPLICATION SPECIFICATIONS:
- Name: {app_name}
- Type / Framework: {app_type} (e.g. FastAPI, Express, React, Flask, Go Gin, Nginx webapp, Spring Boot, etc.)
- Description / Features: {description or f"Production-grade {app_type} application with health checks, API endpoints, and clean UI/JSON responses"}
- Default Port: {port}

REQUIREMENTS:
1. Provide all necessary code files: main entrypoint, configuration, package/dependency descriptor (e.g. requirements.txt or package.json), and README.
2. Provide an optimized multi-stage production Dockerfile:
   - Non-root user for security
   - Proper layer caching
   - Healthcheck instruction (`HEALTHCHECK`)
   - Exposing port {port}
3. Include `/healthz` and `/` endpoints returning application status and readiness.

OUTPUT FORMAT:
Return ONLY a valid JSON object inside ```json ... ``` with the following schema:
```json
{{
  "app_name": "{app_name}",
  "app_type": "{app_type}",
  "port": {port},
  "summary": "Brief summary of generated app components",
  "files": [
    {{
      "path": "app.py",
      "content": "...full source code..."
    }},
    {{
      "path": "requirements.txt",
      "content": "...dependencies..."
    }},
    {{
      "path": "Dockerfile",
      "content": "...multi-stage Dockerfile..."
    }}
  ]
}}
```
"""
        try:
            raw = generate_text_with_retry(self.client, prompt)
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()
            else:
                json_str = raw
            data = json.loads(json_str)

            # Write files to target_dir
            written_files = []
            if not self.dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                for f in data.get("files", []):
                    rel_path = f.get("path", "")
                    content = f.get("content", "")
                    if rel_path and content:
                        file_dest = target_dir / rel_path
                        file_dest.parent.mkdir(parents=True, exist_ok=True)
                        file_dest.write_text(content, encoding='utf-8')
                        written_files.append(str(file_dest))
                        print(f"  ✓ Created: {file_dest.name}")
            else:
                print("  [DRY RUN] Would write scaffolded files to disk:")
                for f in data.get("files", []):
                    print(f"    - {f.get('path')}")

            # Ensure dockerfile path
            dockerfile_path = target_dir / "Dockerfile"
            if not dockerfile_path.exists() and not self.dry_run:
                df_lower = target_dir / "dockerfile"
                if df_lower.exists():
                    dockerfile_path = df_lower

            return {
                "success": True,
                "app_name": app_name,
                "app_type": app_type,
                "app_dir": str(target_dir),
                "dockerfile_path": str(dockerfile_path),
                "port": data.get("port", port),
                "written_files": written_files,
                "summary": data.get("summary", "App scaffolded successfully"),
            }

        except Exception as exc:
            print(f"  ❌ [App Agent] Gemini scaffolding failed: {exc}")
            return self._fallback_scaffold(app_name, app_type, target_dir, port)

    def _fallback_scaffold(self, app_name: str, app_type: str, target_dir: Path, port: int) -> dict:
        """Fallback built-in app scaffold if LLM is unreachable."""
        print("  ⚠️ Using fallback scaffolding template…")
        if not self.dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            
            app_code = f"""from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

PORT = int(os.getenv("PORT", "{port}"))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/healthz':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({{"status": "healthy", "app": "{app_name}"}}).encode())
            return
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>{app_name} on Azure</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .card {{ background: #1e293b; padding: 2.5rem; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); text-align: center; border: 1px solid #334155; }}
        h1 {{ color: #38bdf8; margin-top: 0; }}
        .badge {{ display: inline-block; background: #0284c7; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 0.875rem; }}
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">Azure Landing Zone</span>
        <h1>🚀 {app_name} is Running!</h1>
        <p>Deployed seamlessly with AI Agents & Azure Kubernetes Service.</p>
        <p><small>Environment: Azure AKS | Port: {port}</small></p>
    </div>
</body>
</html>'''
        self.wfile.write(html.encode())

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f"Serving on port {{PORT}}...")
    server.serve_forever()
"""
            (target_dir / "app.py").write_text(app_code, encoding='utf-8')
            
            dockerfile_content = f"""FROM python:3.11-slim
WORKDIR /app
COPY app.py .
EXPOSE {port}
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}/healthz')" || exit 1
CMD ["python", "app.py"]
"""
            (target_dir / "Dockerfile").write_text(dockerfile_content, encoding='utf-8')

        return {
            "success": True,
            "app_name": app_name,
            "app_type": app_type,
            "app_dir": str(target_dir),
            "dockerfile_path": str(target_dir / "Dockerfile"),
            "port": port,
            "written_files": [str(target_dir / "app.py"), str(target_dir / "Dockerfile")],
            "summary": "Fallback application template generated.",
        }

    def generate_manifests(
        self,
        app_name: str,
        image_ref: str,
        port: int = 80,
        namespace: str = "default",
        replicas: int = 2,
        target_k8s_dir: Path = None,
        env_vars: dict = None,
    ) -> list[Path]:
        """
        Generate enterprise Kubernetes manifests for the application.
        """
        if not target_k8s_dir:
            target_k8s_dir = REPO_ROOT / "k8s"

        print(f"\n📦 [App Agent] Generating Kubernetes manifests for '{app_name}' (Image: {image_ref}, Port: {port})…")

        env_json = json.dumps(env_vars or {})

        prompt = f"""You are a Kubernetes Specialist for Azure AKS.
Generate complete, production-ready Kubernetes manifests for this application:

- Application Name: {app_name}
- Container Image: {image_ref}
- Container Port: {port}
- Target Namespace: {namespace}
- Replicas: {replicas}
- Environment Variables: {env_json}

MANIFEST REQUIREMENTS:
1. Namespace manifest (if not default)
2. Deployment manifest with:
   - Resource requests (cpu: 100m, memory: 128Mi) and limits (cpu: 500m, memory: 512Mi)
   - Liveness Probe (httpGet path: /healthz or /, port: {port})
   - Readiness Probe (httpGet path: /healthz or /, port: {port})
   - Security Context (runAsNonRoot: true, allowPrivilegeEscalation: false)
   - imagePullPolicy: Always
3. Service manifest (type: LoadBalancer or ClusterIP, port: 80 or {port}, targetPort: {port})
4. HorizontalPodAutoscaler (HPA) manifest (min: 2, max: 10, targetCPU: 75%)
5. ConfigMap manifest for app configuration

Return ONLY valid YAML separated by '---' inside a ```yaml block.
"""
        manifest_file = target_k8s_dir / f"{app_name}-deployment.yaml"
        
        try:
            raw = generate_text_with_retry(self.client, prompt)
            if "```yaml" in raw:
                yaml_content = raw.split("```yaml")[1].split("```")[0].strip()
            elif "```" in raw:
                yaml_content = raw.split("```")[1].split("```")[0].strip()
            else:
                yaml_content = raw
        except Exception as exc:
            print(f"  [WARN] Gemini manifest generation failed: {exc}. Using robust standard template.")
            yaml_content = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
      - name: {app_name}
        image: {image_ref}
        imagePullPolicy: Always
        ports:
        - containerPort: {port}
          name: http
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        readinessProbe:
          httpGet:
            path: /
            port: {port}
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /
            port: {port}
          initialDelaySeconds: 15
          periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: {app_name}-service
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  type: LoadBalancer
  selector:
    app: {app_name}
  ports:
  - protocol: TCP
    port: 80
    targetPort: {port}
"""

        if not self.dry_run:
            target_k8s_dir.mkdir(parents=True, exist_ok=True)
            manifest_file.write_text(yaml_content, encoding='utf-8')
            print(f"  ✓ Manifest created: {manifest_file.relative_to(REPO_ROOT) if manifest_file.is_relative_to(REPO_ROOT) else manifest_file}")
        else:
            print(f"  [DRY RUN] Would write manifest to: {manifest_file.name}")

        return [manifest_file]


class AppAgent:
    """
    Main AppAgent entrypoint class for the orchestrator.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.scaffolder = AppScaffolder(dry_run=dry_run)

    def run(self, args: dict) -> dict:
        """
        Execute app inspection/scaffolding and manifest generation.
        """
        app_name = args.get("app_name") or "azure-app"
        app_type = args.get("app_type") or "fastapi"
        app_desc = args.get("app_description") or args.get("description") or ""
        app_dir_str = args.get("app_dir") or args.get("source_dir")
        port = int(args.get("port") or 80)
        namespace = args.get("namespace") or "default"
        image_ref = args.get("image_ref") or f"{app_name}:latest"

        target_dir = Path(app_dir_str) if app_dir_str else (REPO_ROOT / "apps" / app_name)
        
        # 1. If directory exists and has files, inspect it
        inspection = self.scaffolder.inspect_directory(target_dir) if target_dir.exists() else {"exists": False}
        
        # 2. Scaffold if not exists or requested
        if not inspection.get("exists") or not inspection.get("has_dockerfile") or args.get("force_scaffold"):
            scaffold_result = self.scaffolder.scaffold_application(
                app_name=app_name,
                app_type=app_type,
                description=app_desc,
                target_dir=target_dir,
                port=port,
            )
            port = scaffold_result.get("port", port)
            dockerfile_path = scaffold_result.get("dockerfile_path")
        else:
            print(f"  ✓ Using existing application in {target_dir}")
            dockerfile_path = str(target_dir / "Dockerfile" if (target_dir / "Dockerfile").exists() else target_dir / "dockerfile")

        # 3. Generate K8s Manifests
        k8s_dir = REPO_ROOT / "k8s"
        manifest_files = self.scaffolder.generate_manifests(
            app_name=app_name,
            image_ref=image_ref,
            port=port,
            namespace=namespace,
            target_k8s_dir=k8s_dir,
        )

        return {
            "success": True,
            "app_name": app_name,
            "app_type": app_type,
            "app_dir": str(target_dir),
            "dockerfile_path": dockerfile_path,
            "manifest_files": [str(m) for m in manifest_files],
            "port": port,
            "namespace": namespace,
        }


def main():
    parser = argparse.ArgumentParser(description="App Agent — Software Scaffolder & K8s Manifest Generator")
    parser.add_argument("--app-name", default="azure-app", help="Application name")
    parser.add_argument("--app-type", default="fastapi", help="Application framework (fastapi, nodejs, react, go, nginx, etc.)")
    parser.add_argument("--description", default="", help="Application description or requirements")
    parser.add_argument("--app-dir", default=None, help="Target application source directory")
    parser.add_argument("--port", type=int, default=80, help="Application listening port")
    parser.add_argument("--namespace", default="default", help="Kubernetes namespace")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing files")
    args = parser.parse_args()

    agent = AppAgent(dry_run=args.dry_run)
    result = agent.run({
        "app_name": args.app_name,
        "app_type": args.app_type,
        "app_description": args.description,
        "app_dir": args.app_dir,
        "port": args.port,
        "namespace": args.namespace,
    })
    print("\n✅ [App Agent] Execution Finished:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
