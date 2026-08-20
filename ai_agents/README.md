# 🧠 Azure AI Autonomous Deployment Command Center

> **Single-Command, Natural-Language Infrastructure & Software Application Deployer powered by Google Gemini and Autonomous AI Agents.**

[![Gemini 2.5](https://img.shields.io/badge/LLM-Gemini_2.5_Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform_1.5%2B-623CE4?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/Orchestration-Azure_AKS-326CE5?logo=kubernetes&logoColor=white)](https://azure.microsoft.com/en-us/products/kubernetes-service)
[![Docker](https://img.shields.io/badge/Containers-Azure_ACR-0089D6?logo=docker&logoColor=white)](https://azure.microsoft.com/en-us/products/container-registry)

---

## 🌟 Overview

The **Azure AI Deployment Command Center** allows you to describe **ANY** software application or infrastructure requirement in plain English. The Master LLM coordinates four specialised autonomous agents to scaffold the application, generate production Dockerfiles and Kubernetes manifests, provision Azure Landing Zone infrastructure via Terraform, build and push containers to ACR, roll out workloads to AKS, and monitor/self-heal GitHub Actions CI/CD pipelines.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │       Master LLM Controller (deploy_cli.py / Web UI)     │
                  │        "deploy a python fastapi microservice to dev"    │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │      Orchestrator      │
                                  │   (Shared Context DB)  │
                                  └────────────┬───────────┘
                                               │
         ┌─────────────────────┬───────────────┴───────────────┬─────────────────────┐
         ▼                     ▼                               ▼                     ▼
┌──────────────────┐  ┌──────────────────┐           ┌──────────────────┐  ┌──────────────────┐
│    App Agent     │  │ Terraform Agent  │           │   K8s/ACR Agent  │  │  Pipeline Agent  │
│                  │  │                  │           │                  │  │                  │
│ • Inspects /     │  │ • Audits .tf code│           │ • az acr build   │  │ • Monitors runs  │
│   Scaffolds any  │  │ • Auto-fixes HCL │           │ • az aks creds   │  │ • Gemini triage  │
│   app (FastAPI,  │  │ • Plans & Applies│           │ • kubectl apply  │  │ • Code fix &     │
│   React, Go, etc)│  │ • Dev / Prod env │           │ • Health checks  │  │   auto-rerun     │
│ • Gen Dockerfile │  │ • Recovery Loop  │           │ • Self-healing   │  │ • Git PR creator │
│ • Gen K8s YAML   │  │                  │           │                  │  │                  │
└──────────────────┘  └──────────────────┘           └──────────────────┘  └──────────────────┘
```

---

## 🚀 Quick Start & Single-Command Usage

### 1. Single Command Execution (CLI)

Deploy any software application stack with one command:

```bash
# Python FastAPI Microservice
python ai_agents/deploy_cli.py "deploy a python fastapi microservice with redis to dev"

# Fullstack React + Node.js Application
python ai_agents/deploy_cli.py "deploy a fullstack react frontend and nodejs backend to aks"

# High-Performance Golang Microservice
python ai_agents/deploy_cli.py "deploy a golang gin api with health check to dev"

# Nginx Static / Portfolio Web App
python ai_agents/deploy_cli.py "deploy an nginx web application to dev"

# Deploy Existing Custom Code
python ai_agents/deploy_cli.py --app-dir ./my-custom-app "deploy my existing app to azure"

# Infrastructure Provisioning Only
python ai_agents/deploy_cli.py "audit and deploy terraform landing zone in dev"

# Safe Dry-Run Simulation
python ai_agents/deploy_cli.py --dry-run "deploy fastapi microservice to prod"
```

Using the root launcher (`deploy.bat` or `./deploy`):
```bash
deploy "deploy a python fastapi microservice to dev"
```

---

### 2. Visual Web Command Center (Dashboard)

Launch the modern real-time Web UI dashboard:

```bash
python ai_agents/deploy_cli.py --web
# or
python ai_agents/web_ui.py --port 5000
```
Open **`http://localhost:5000`** in your browser to interact with the LLM visually, view the active multi-agent pipeline graph, and inspect real-time streaming execution logs.

---

### 3. Interactive CLI Chat REPL

```bash
python ai_agents/deploy_cli.py --interactive
```

---

## 🤖 The Four Autonomous Agents

### 1. 📦 App Agent (`app_agent/app_agent.py`)
- **Inspection**: Analyzes any local folder to detect language, framework, dependencies, ports, and entrypoints.
- **Dynamic Scaffolding**: If generating a new app, asks Gemini to generate full application source code (FastAPI, Node.js Express, React, Flask, Go Gin, Spring Boot, Nginx, etc.).
- **Enterprise Dockerfile**: Multi-stage build, non-root user, layer caching, and healthcheck probe.
- **Kubernetes Manifests**: Deployment, Service LoadBalancer, Ingress, HPA, ConfigMap.

### 2. 🏗️ Terraform Agent (`terraform_agent/terraform_agent.py`)
- **Security & Best-Practice Audit**: Audits all `.tf` files in `Terraform/` with Gemini.
- **Auto-Fix**: Rewrites misconfigured HCL files automatically.
- **Provisioning**: Executes `terraform init ➔ plan ➔ apply` in the specified environment (`dev`, `no-prod`, `prod`).
- **Error-Rectify Loop**: If `terraform apply` fails, captures stderr, asks Gemini for corrections, applies them, and retries.

### 3. ☸️ Kubernetes & ACR Agent (`k8s_acr_agent/k8s_acr_agent.py`)
- **ACR Build**: Builds container image via `az acr build` with zero local Docker daemon dependencies.
- **AKS Integration**: Retrieves cluster credentials via `az aks get-credentials`.
- **Manifest Application**: Applies generated manifests with `kubectl apply`.
- **Health Verification**: Polls `kubectl rollout status` until all pods are Ready and outputs external LoadBalancer IP.
- **Self-Healing**: If kubectl fails, diagnoses error with Gemini, patches YAML, and re-applies.

### 4. 🔄 Pipeline Agent (`pipeline_agent/pipeline_agent.py`)
- **GitHub Actions Monitor**: Fetches latest workflow run status via GitHub API / `gh` CLI.
- **Log Diagnostic**: Retrieves failed job logs and prompts Gemini for exact root causes.
- **Automated Fix & Re-trigger**: Commits fixes to branch, pushes to GitHub, and re-triggers workflow runs until green.

---



## 🧪 Verification & Testing

Run `--show-plan-only` or `--dry-run` to test intent parsing and agent execution without modifying cloud resources:

```bash
python ai_agents/deploy_cli.py --show-plan-only "deploy a python fastapi app with redis to dev"
python ai_agents/deploy_cli.py --dry-run "deploy fullstack react and nodejs app to aks"
```
