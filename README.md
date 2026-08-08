# ☁️ Azure Landing Zone with Terraform

### Production-Style Azure Infrastructure Automation using Terraform & GitHub Actions

**Azure • Terraform • GitHub Actions • OIDC • IaC • DevSecOps**

---

## 📌 Project Overview

This project demonstrates the design and deployment of a **modular, production-style Azure Landing Zone** using **Terraform** and an automated **GitHub Actions CI/CD pipeline**.

The implementation follows real-world **Cloud, DevOps, DevSecOps, and Infrastructure-as-Code best practices**, including:

* 🧩 Modular and reusable Terraform architecture
* 🌍 Environment-based infrastructure configuration
* 🗄️ Azure Blob Storage-based Terraform Remote State
* 🔐 Secretless GitHub-to-Azure authentication using OIDC
* ⚙️ Automated Terraform CI/CD using GitHub Actions
* 🛡️ Infrastructure security and quality scanning
* 🌿 Pull Request-based infrastructure workflow
* 🔒 Azure RBAC-based access control
* 🔄 Terraform Plan → Review → Apply deployment model
* 🧪 Infrastructure idempotency validation

---

# 🏗️ Architecture Overview

The infrastructure follows a controlled GitOps-style workflow:

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
┌──────────────────────────────┐
│       Terraform CI           │
│                              │
│  • Format & Validate         │
│  • TFLint                    │
│  • tfsec                     │
│  • Checkov                   │
│  • Trivy                     │
│  • Gitleaks                  │
│  • Terraform Plan            │
└──────────────┬───────────────┘
               │
          Code Review
               │
               ▼
             main
               │
               ▼
┌──────────────────────────────┐
│       Terraform CD           │
│                              │
│  • OIDC Authentication       │
│  • Terraform Init             │
│  • Terraform Validate         │
│  • Terraform Plan             │
│  • Plan Artifact              │
│  • Terraform Apply            │
└──────────────┬───────────────┘
               │
              OIDC
               │
               ▼
       Microsoft Entra ID
               │
               ▼
          Azure RBAC
               │
               ▼
      ☁️ Microsoft Azure
```

The Azure Landing Zone provisions foundational infrastructure across networking, security, compute, identity, and application delivery layers.

---

# ✨ Key Engineering Decisions

## 🔐 Secretless Azure Authentication

GitHub Actions authenticates to Azure using **OpenID Connect (OIDC)** instead of storing long-lived Azure client secrets.

```text
GitHub Actions
      │
      ▼
  OIDC Token
      │
      ▼
Microsoft Entra ID
      │
      ▼
Federated Credential
      │
      ▼
Service Principal
      │
      ▼
 Azure RBAC
```

This eliminates the need to store long-lived Azure credentials inside GitHub and provides a more secure authentication model for CI/CD automation.

---

# 🗄️ Centralized Terraform Remote State

Terraform state is stored remotely in **Azure Blob Storage** instead of using local state files.

```text
Resource Group
      │
      ▼
Azure Storage Account
      │
      ▼
Blob Container
      │
      ▼
Terraform State
```

### Benefits

* ☁️ Centralized Terraform state
* 🔒 State locking
* 🤝 Team collaboration
* ⚙️ GitHub Actions compatibility
* 💾 Protection against local state loss
* 🔄 Consistent state between local development and CI/CD

The remote backend allows local Terraform executions and GitHub Actions to work against the same infrastructure state.

---

# 🥾 Terraform Backend Bootstrap

A separate Terraform configuration is used to provision the infrastructure required by the Terraform backend.

```text
Bootstrap Terraform
       │
       ├── Resource Group
       ├── Storage Account
       └── Blob Container
                │
                ▼
        Terraform Remote State
```

The bootstrap workflow is managed independently through:

```text
.github/workflows/terraform-bootstrap.yml
```

This solves the **Terraform backend bootstrap dependency**, because the remote backend must exist before the main Terraform configuration can use it.

---

# 🧩 Modular Terraform Architecture

The infrastructure is implemented using **reusable Terraform child modules** rather than maintaining the entire infrastructure in a single Terraform configuration.

This improves:

* Reusability
* Maintainability
* Environment consistency
* Separation of responsibilities
* Scalability of the Terraform codebase

```text
Root / Environment Module
          │
          ├── Networking Modules
          ├── Security Modules
          ├── Compute Modules
          ├── Application Modules
          └── Identity / RBAC Modules
```

---

# ☁️ Azure Infrastructure

The Terraform implementation manages the following Azure components:

| Category                  | Azure Resources                 |
| ------------------------- | ------------------------------- |
| 📦 Resource Management    | Resource Groups                 |
| 🌐 Networking             | Virtual Network, Subnets        |
| 🔒 Network Security       | NSGs, NSG Associations          |
| 🌍 Public Connectivity    | Public IP Addresses             |
| 🚪 Outbound Connectivity  | NAT Gateway & Associations      |
| 🛡️ Secure Administration | Azure Bastion                   |
| ⚖️ Application Traffic    | Application Gateway             |
| 🖥️ Compute               | Linux Virtual Machines          |
| 🔌 Networking             | Network Interfaces              |
| 🔐 Secrets Management     | Azure Key Vault                 |
| 🔑 Secrets                | Key Vault Secrets               |
| 👤 Access Control         | Key Vault RBAC Role Assignments |

---


# 🌿 PR-Based Infrastructure Workflow

All infrastructure changes follow a controlled Pull Request workflow:

```text
Feature Branch
      │
      ▼
Terraform Changes
      │
      ▼
Pull Request
      │
      ▼
Terraform CI
      │
      ▼
Code Review
      │
      ▼
Merge → main
      │
      ▼
Terraform CD
```

Direct changes to the `main` branch are restricted through **GitHub Branch Protection**.

---

# 🔄 Terraform CI Pipeline

The CI pipeline validates infrastructure changes before they are merged.

```text
Pull Request
      │
      ▼
Checkout Repository
      │
      ▼
Azure OIDC Authentication
      │
      ▼
Terraform Init
      │
      ▼
Terraform Validate
      │
      ▼
Security & Quality Scanning
      │
      ├── TFLint
      ├── tfsec
      ├── Checkov
      ├── Trivy
      └── Gitleaks
      │
      ▼
Terraform Plan
      │
      ▼
CI Result
```

The objective is to identify:

* Terraform syntax/configuration issues
* Code-quality problems
* Security misconfigurations
* IaC policy violations
* Vulnerable infrastructure definitions
* Accidentally committed secrets

before changes reach the `main` branch.

---

# 🚀 Terraform CD Pipeline

After infrastructure code is validated and merged into `main`, the CD workflow performs the deployment.

```text
main
 │
 ▼
Terraform CD
 │
 ▼
Azure OIDC Login
 │
 ▼
Terraform Init
 │
 ▼
Terraform Validate
 │
 ▼
Terraform Plan
 │
 ▼
Upload Plan Artifact
 │
 ▼
Apply Job
 │
 ▼
Download Plan Artifact
 │
 ▼
Terraform Apply
 │
 ▼
☁️ Azure Infrastructure
```

A key design decision is that the **Terraform plan generated during the Plan job is stored as an artifact and then consumed by the Apply job**.

This ensures that the reviewed Terraform plan is the plan that gets applied.

---

# 🛡️ Security & Code Quality

Multiple tools are integrated into the Terraform CI pipeline:

| Tool        | Purpose                                     |
| ----------- | ------------------------------------------- |
| 🔍 TFLint   | Terraform linting and configuration quality |
| 🛡️ tfsec   | Terraform security scanning                 |
| ✅ Checkov   | IaC policy and misconfiguration scanning    |
| 🔎 Trivy    | Infrastructure-as-Code security scanning    |
| 🔑 Gitleaks | Detection of accidentally committed secrets |

Security reports are maintained under:

```text
security_tool_reports/
```

---

# 🧪 Terraform Idempotency Validation

After the initial infrastructure deployment, the Terraform CD pipeline was executed again without modifying the Terraform configuration.

Terraform returned:

```text
No changes. Your infrastructure matches the configuration.
```

This validates that:

* Terraform state matches the deployed Azure infrastructure
* Remote state is functioning correctly
* Re-running the same configuration does not unnecessarily recreate resources
* The infrastructure configuration is behaving idempotently

---

# 🧹 Infrastructure Cleanup

A manually triggered Terraform destroy workflow is available for controlled environment cleanup.

```text
.github/workflows/terraform-destroy.yml
```

The workload infrastructure can be destroyed while keeping the separately managed Terraform backend infrastructure available for future deployments.

The destroy workflow is intentionally **manual** and is not automatically triggered.

---

# 🔄 End-to-End DevOps Flow

```text
Developer
    │
    ▼
Feature Branch
    │
    ▼
Terraform Code
    │
    ▼
Pull Request
    │
    ▼
┌────────────────────────┐
│     Terraform CI       │
│                        │
│  • Validate            │
│  • Lint                │
│  • Security Scan       │
│  • Terraform Plan      │
└───────────┬────────────┘
            │
            ▼
       Code Review
            │
            ▼
       Merge → main
            │
            ▼
┌────────────────────────┐
│     Terraform CD       │
│                        │
│  • OIDC Authentication │
│  • Terraform Init      │
│  • Terraform Plan      │
│  • Terraform Apply     │
└───────────┬────────────┘
            │
            ▼
     Microsoft Azure
            │
            ▼
    Landing Zone Infra
```

---

# 🧰 Technology Stack

| Area              | Technologies                                               |
| ----------------- | ---------------------------------------------------------- |
| ☁️ Cloud          | Microsoft Azure                                            |
| 🏗️ IaC           | Terraform, AzureRM Provider                                |
| ⚙️ CI/CD          | GitHub Actions                                             |
| 🔐 Identity       | Microsoft Entra ID, OIDC Federation                        |
| 🛡️ Security      | Checkov, tfsec, Trivy, Gitleaks, TFLint                    |
| 🌐 Networking     | Azure VNet, Subnets, NSG, NAT Gateway, Application Gateway |
| 🔑 Secrets        | Azure Key Vault                                            |
| 🖥️ Compute       | Azure Linux Virtual Machines                               |
| 🗄️ State         | Azure Storage / Blob Remote State                          |
| 🌿 Source Control | Git, GitHub                                                |
| 🔒 Authorization  | Azure RBAC                                                 |
| 📋 Workflow       | Pull Requests, Branch Protection                           |
| 📄 Configuration  | YAML, Terraform                                            |

---

# 🎯 Key Learning Outcomes

This project demonstrates practical experience in:

* Designing modular Terraform infrastructure
* Building reusable Terraform child modules
* Managing Terraform Remote State using Azure Storage
* Solving the Terraform backend bootstrap dependency
* Implementing GitHub Actions CI/CD
* Configuring GitHub OIDC federation with Azure
* Implementing Azure RBAC for automation identities
* Integrating IaC security scanning into CI/CD
* Implementing protected branch and Pull Request workflows
* Managing Terraform Plan → Apply workflows
* Troubleshooting Azure authorization and RBAC issues
* Validating Terraform infrastructure idempotency

---

# 🔮 Future Enhancements

Potential future improvements include:

* 📐 Detailed Draw.io architecture diagram
* 🔒 Additional infrastructure security hardening
* 🏷️ Standardized Azure tagging strategy
* 🧪 Additional Terraform validation and testing
* 👥 GitHub CODEOWNERS integration
* 🛡️ Enhanced branch protection policies
* 📊 Azure monitoring and diagnostic settings
* 💰 Cost-management controls

---

# ⭐ Project Summary

This project represents a **production-style Azure Infrastructure-as-Code implementation** that combines **Terraform modularization, secure OIDC authentication, centralized remote state, automated CI/CD, IaC security scanning, Azure RBAC, and controlled Pull Request-based infrastructure delivery**.

The overall objective is to demonstrate how Azure infrastructure can be **securely, consistently, and repeatably deployed through an automated DevSecOps workflow** rather than through manual portal-based provisioning.
