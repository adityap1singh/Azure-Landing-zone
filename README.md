# ☁️ Azure Landing Zone with Terraform

[![Terraform](https://img.shields.io/badge/Terraform-1.5%2B-623CE4?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![Azure](https://img.shields.io/badge/Microsoft_Azure-Landing_Zone-0089D6?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![DevSecOps](https://img.shields.io/badge/DevSecOps-Security_Scanned-brightgreen?logo=shield&logoColor=white)](#-security--code-quality)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Production-Style Azure Infrastructure Automation using Terraform, OIDC, & GitHub Actions**

---

## 📋 Table of Contents

- [📌 Project Overview](#-project-overview)
- [📁 Repository Structure](#-repository-structure)
- [🏗️ Architecture Overview](#️-architecture-overview)
- [✨ Key Engineering Decisions](#-key-engineering-decisions)
- [☁️ Azure Infrastructure Resources](#️-azure-infrastructure-resources)
- [🌿 PR-Based Infrastructure Workflow](#-pr-based-infrastructure-workflow)
- [🔄 Terraform CI/CD Pipeline](#-terraform-cicd-pipeline)
- [🛡️ Security & Code Quality](#️-security--code-quality)
- [🚀 Getting Started](#-getting-started)
- [🧪 Terraform Idempotency Validation](#-terraform-idempotency-validation)
- [🧹 Infrastructure Cleanup](#-infrastructure-cleanup)
- [🧰 Technology Stack](#-technology-stack)
- [🎯 Key Learning Outcomes](#-key-learning-outcomes)
- [🔮 Future Enhancements](#-future-enhancements)

---

## 📌 Project Overview

This project demonstrates the design and deployment of a **modular, enterprise-ready Azure Landing Zone** using **Terraform** and an automated **GitHub Actions CI/CD pipeline**. 

The implementation adheres to real-world **Cloud Architecture, DevOps, DevSecOps, and Infrastructure-as-Code (IaC) best practices**, including:

* 🧩 **Modular Architecture**: 11 reusable child modules for scalable provisioning
* 🌍 **Multi-Environment Support**: Structured environments (`dev`, `no-prod`, `prod`)
* 🗄️ **Centralized State**: Remote backend state stored in Azure Blob Storage with state locking
* 🔐 **Secretless Auth**: OpenID Connect (OIDC) identity federation with Microsoft Entra ID
* ⚙️ **Automated CI/CD**: Automated linting, security scanning, plan generation, and deployment
* 🛡️ **DevSecOps Security Gate**: Automated scanning with TFLint, tfsec, Checkov, Trivy, & Gitleaks
* 🌿 **GitOps Workflow**: Pull Request controls, branch protection, and code reviews
* 🔄 **Idempotency**: Deterministic infrastructure updates preventing unintended drift

---

## 📁 Repository Structure

```text
Azure-Landing-zone/
├── .github/
│   └── workflows/
│       ├── ci.yaml                    # Terraform CI pipeline (lint, scan, plan)
│       └── cd.yaml                    # Terraform CD pipeline (apply to Azure)
├── Terraform/
│   ├── child_module/                  # Reusable Infrastructure Child Modules
│   │   ├── Bastion_host/              # Azure Bastion service
│   │   ├── Network_interface/         # VM Network Interfaces (NIC)
│   │   ├── acr_registry/              # Azure Container Registry (ACR)
│   │   ├── kubernetes_service/        # Azure Kubernetes Service (AKS)
│   │   ├── network_security_group/    # Network Security Groups & Rules
│   │   ├── resource_group/            # Azure Resource Groups
│   │   ├── storage_account/           # Azure Storage Accounts
│   │   ├── storage_container/         # Blob Storage Containers
│   │   ├── subnet/                    # VNet Subnets
│   │   ├── virtual_machine/           # Linux Virtual Machines
│   │   └── virtual_network/           # Virtual Networks (VNet)
│   └── environment/                   # Root Modules per Environment
│       ├── dev/                       # Development environment configuration
│       ├── no-prod/                    # Non-production environment configuration
│       └── prod/                      # Production environment configuration
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🏗️ Architecture Overview

The infrastructure follows a controlled GitOps-style deployment model:

```text
Developer
   │
   ▼
Feature Branch
   │
   ▼
Pull Request
   │
   ▼
┌────────────────────────────────────────────────────────┐
│                      Terraform CI                      │
│                                                        │
│  • Format & Validate    • TFLint     • tfsec           │
│  • Checkov              • Trivy      • Gitleaks        │
│  • Terraform Plan                                      │
└───────────────────────────┬────────────────────────────┘
                            │
                       Code Review
                            │
                            ▼
                          main
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                      Terraform CD                      │
│                                                        │
│  • OIDC Authentication   • Terraform Init              │
│  • Terraform Validate    • Terraform Plan              │
│  • Upload Plan Artifact  • Terraform Apply             │
└───────────────────────────┬────────────────────────────┘
                            │
                        OIDC Token
                            │
                            ▼
                   Microsoft Entra ID
                            │
                            ▼
                       Azure RBAC
                            │
                            ▼
          ☁️ Microsoft Azure Landing Zone
```

---

## ✨ Key Engineering Decisions

### 🔐 Secretless Azure Authentication (OIDC)

GitHub Actions authenticates to Azure dynamically using **OpenID Connect (OIDC)** federated credentials rather than storing long-lived client secrets inside repository secrets.

```text
GitHub Actions ──► OIDC Token ──► Entra ID (Federated Credential) ──► Service Principal ──► Azure RBAC
```

**Benefits**:
* Eliminates credential exposure and secret rotation overhead
* Scope-restricted authentication for CI/CD runs
* Aligns with Zero Trust architecture guidelines

---

### 🗄️ Centralized Terraform Remote State

Terraform state is stored securely in **Azure Blob Storage** with state locking to support concurrent team workflows and CI/CD pipelines.

```text
Azure Resource Group ──► Storage Account ──► Blob Container ──► terraform.tfstate (Locked)
```

**Benefits**:
* Protection against local state loss
* Concurrent state locking prevents conflicting modifications
* Shared state access across local CLI and GitHub Actions runners

---

### 🧩 Modular & Multi-Environment Architecture

The codebase strictly decouples infrastructure resource definitions into **child modules** (`Terraform/child_module/`) and consumes them inside environment-specific root modules (`Terraform/environment/`):

```text
Terraform/environment/{dev, no-prod, prod}
               │
               ├──► child_module/virtual_network
               ├──► child_module/subnet
               ├──► child_module/network_security_group
               ├──► child_module/kubernetes_service
               ├──► child_module/acr_registry
               └──► child_module/virtual_machine
```

---

## ☁️ Azure Infrastructure Resources

The Landing Zone provisions and manages the following core Azure resources:

| Category | Azure Component | Description |
| :--- | :--- | :--- |
| 📦 **Resource Management** | Azure Resource Groups | Logical containers for target workloads |
| 🌐 **Networking** | Virtual Networks (VNet) & Subnets | Isolated cloud network topologies |
| 🔒 **Security** | Network Security Groups (NSG) | Inbound & outbound network firewalls |
| 🛡️ **Administration** | Azure Bastion | Secure RDP/SSH access without public IPs |
| 📦 **Containers** | Azure Container Registry (ACR) | Private Docker container image repository |
| ☸️ **Orchestration** | Azure Kubernetes Service (AKS) | Managed Kubernetes compute clusters |
| 🖥️ **Compute** | Linux Virtual Machines & NICs | Virtualized host compute instances |
| 🗄️ **Storage** | Azure Storage Account & Containers | Remote state & persistent object storage |

---

## 🌿 PR-Based Infrastructure Workflow

All infrastructure updates follow a strict Pull Request strategy:

```text
Feature Branch ──► Terraform Changes ──► Pull Request ──► Automated CI ──► Code Review ──► Merge main ──► Automated CD
```

* **Branch Protection**: Direct commits to `main` are blocked.
* **Plan Verification**: Terraform plan output is automatically posted to PRs for reviewer inspection.

---

## 🔄 Terraform CI/CD Pipeline

The pipeline is split into two automated GitHub Actions workflows:

### 1. 🔍 Terraform CI (`.github/workflows/ci.yaml`)
Triggered on **Pull Requests** targeting `main`:
1. **Checkout & OIDC Authentication**
2. **Terraform Format & Validation** (`terraform fmt`, `terraform validate`)
3. **Security & Compliance Scanning**:
   - `TFLint`: Terraform syntax linting
   - `tfsec`: Security misconfiguration scanner
   - `Checkov`: Policy-as-Code evaluation
   - `Trivy`: Vulnerability scanning
   - `Gitleaks`: Secret detection
4. **Terraform Plan Generation**: Creates speculative plan output for inspection.

### 2. 🚀 Terraform CD (`.github/workflows/cd.yaml`)
Triggered on **Push to `main`**:
1. **Azure OIDC Authentication**
2. **Terraform Initialization & Validation**
3. **Terraform Plan & Artifact Generation**: Saves state plan artifact.
4. **Terraform Apply**: Applies the precise verified plan artifact to Azure.

---

## 🛡️ Security & Code Quality

Security checks are enforced at every step in the pipeline:

| Tool | Focus Area | Role in Pipeline |
| :--- | :--- | :--- |
| 🔍 **TFLint** | Code Quality | Flags unused variables, deprecated syntax, & cloud-provider rules |
| 🛡️ **tfsec** | Security | Detects overly permissive security group rules & unencrypted resources |
| ✅ **Checkov** | Compliance | Evaluates policies against CIS benchmarks & best practices |
| 🔎 **Trivy** | Vulnerabilities | Scans IaC templates & dependencies for known CVEs |
| 🔑 **Gitleaks** | Secret Protection | Scans commit history for hardcoded API keys, tokens, or passwords |

---

## 🚀 Getting Started

### Prerequisites

* [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) (`v1.5.0+`)
* [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) (`v2.50.0+`)
* An active **Azure Subscription**
* Configured Azure Storage Account for remote backend state

### Local Execution Step-by-Step

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/Azure-Landing-zone.git
   cd Azure-Landing-zone/Azure-Landing-zone/Terraform/environment/dev
   ```

2. **Authenticate with Azure**:
   ```bash
   az login
   az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
   ```

3. **Initialize Terraform Backend**:
   ```bash
   terraform init
   ```

4. **Validate & Plan**:
   ```bash
   terraform validate
   terraform plan -out=tfplan
   ```

5. **Apply Infrastructure Changes**:
   ```bash
   terraform apply tfplan
   ```

---

## 🧪 Terraform Idempotency Validation

Infrastructure idempotency has been verified by running consecutive deployment pipelines without code changes:

```text
No changes. Your infrastructure matches the configuration.
```

This confirms that state locking, drift detection, and remote state synchronization are fully operational.

---

## 🧹 Infrastructure Cleanup

To destroy deployed workload infrastructure in a controlled environment:

```bash
cd Terraform/environment/dev
terraform destroy
```

Alternatively, invoke the manual **Terraform Destroy** GitHub Actions workflow (`.github/workflows/terraform-destroy.yml` if configured).

---

## 🧰 Technology Stack

* **Cloud Platform**: Microsoft Azure
* **Infrastructure as Code**: Terraform (`azurerm` provider)
* **CI/CD Automation**: GitHub Actions
* **Authentication**: Microsoft Entra ID (OIDC Federation)
* **Containerization & Kubernetes**: Azure Container Registry (ACR), Azure Kubernetes Service (AKS)
* **Security Scanners**: Checkov, tfsec, Trivy, Gitleaks, TFLint
* **Networking & Security**: Azure VNet, Subnets, NSG, Azure Bastion, Network Interfaces

---

## 🎯 Key Learning Outcomes

- Building modular and scalable enterprise Terraform codebases
- Setting up secretless OIDC authentication between GitHub Actions & Azure Entra ID
- Implementing multi-environment architecture (`dev`, `no-prod`, `prod`)
- Enforcing IaC security scanning & policy compliance gates in CI/CD pipelines
- Managing Terraform remote state with locking in Azure Blob Storage
- Achieving deterministic, idempotent infrastructure provisioning

---

## 🔮 Future Enhancements

- 📊 Azure Monitor & Log Analytics workspace integration
- 🛡️ Azure Policy assignment integration via Terraform
- 💰 Automated cost optimization & budget alerts
- 🏷️ Azure-wide standardized resource tagging policies

---

## 📄 License

Distributed under the [MIT License](LICENSE).

---

## ⭐ Project Summary

This project represents a **production-style Azure Infrastructure-as-Code implementation** that combines **Terraform modularization, secure OIDC authentication, centralized remote state, automated CI/CD, IaC security scanning, Azure RBAC, and controlled Pull Request-based infrastructure delivery**.

The overall objective is to demonstrate how Azure infrastructure can be **securely, consistently, and repeatably deployed through an automated DevSecOps workflow** rather than through manual portal-based provisioning.

