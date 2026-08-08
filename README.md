☁️ Azure Landing Zone with Terraform
Production-Style Azure Infrastructure Automation using Terraform & GitHub Actions
Azure Terraform GitHub Actions OIDC IaC

Modular Terraform • Remote State • OIDC • CI/CD • Security Scanning

📌 Project Overview
This project demonstrates the deployment of a modular Azure Landing Zone infrastructure using Terraform with an automated GitHub Actions CI/CD workflow.

The project focuses on building infrastructure using real-world DevOps practices such as:

🧩 Modular Terraform architecture
🌍 Environment-based infrastructure configuration
🗄️ Azure Blob Storage Remote Backend
🔐 Secretless GitHub-to-Azure authentication using OIDC
⚙️ Automated CI/CD using GitHub Actions
🛡️ Infrastructure security scanning
🌿 Pull Request based development workflow
🔒 Azure RBAC based access control
🏗️ Architecture Overview
                         Developer
                             │
                             ▼
                       Feature Branch
                             │
                             ▼
                        Pull Request
                             │
                             ▼
              ┌──────────────────────────┐
              │      Terraform CI        │
              │                          │
              │  Format & Validate       │
              │  Security Scanning       │
              │  Terraform Plan          │
              └────────────┬─────────────┘
                           │
                     Review & Merge
                           │
                           ▼
                        main
                           │
                           ▼
              ┌──────────────────────────┐
              │      Terraform CD        │
              │                          │
              │     Plan → Apply         │
              └────────────┬─────────────┘
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
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       Network          Security         Compute
          │                │                │
       VNet             Key Vault          VMs
      Subnets              RBAC             NIC
       NSGs              Secrets
   NAT Gateway
     Bastion
   App Gateway
📐 A detailed Draw.io architecture diagram can be added here for a complete visual representation of the Landing Zone.

✨ Key Engineering Decisions
🔐 Secretless Authentication
GitHub Actions authenticates with Microsoft Azure using OpenID Connect (OIDC) instead of storing long-lived Azure client secrets.

GitHub Actions
      │
      ▼
OIDC Token
      │
      ▼
Microsoft Entra ID
      │
      ▼
App Registration / Service Principal
      │
      ▼
Azure RBAC
🗄️ Centralized Terraform State
Terraform state is stored remotely in Azure Blob Storage, allowing both local Terraform and GitHub Actions to work with the same infrastructure state.

🧩 Modular Infrastructure
Azure resources are implemented using reusable Terraform child modules instead of maintaining the complete infrastructure in a single Terraform configuration.

🌿 PR-Based Infrastructure Changes
Infrastructure changes follow a controlled workflow:

Feature Branch → Pull Request → CI → Review → Merge → CD
Direct changes to the main branch are protected.

☁️ Azure Infrastructure
The Terraform configuration manages the following Azure resources:

Category	Azure Resources
📦 Resource Management	Resource Groups
🌐 Networking	Virtual Network, Subnets
🔒 Network Security	Network Security Groups, NSG Associations
🌍 Public Connectivity	Public IP Addresses
🚪 Outbound Connectivity	NAT Gateway & Associations
🛡️ Secure Administration	Azure Bastion
⚖️ Application Traffic	Application Gateway
🖥️ Compute	Linux Virtual Machines
🔌 Network Interfaces	Azure NICs
🔐 Secrets Management	Azure Key Vault
🔑 Secrets	Key Vault Secrets
👤 Access Control	Key Vault RBAC Role Assignments
📂 Repository Structure
AZ-Landing-Zone-Terraform/
│
├── .github/
│   └── workflows/
│       ├── terraform-bootstrap.yml
│       ├── terraform-ci.yml
│       ├── terraform-cd.yml
│       └── terraform-destroy.yml
│
├── bootstrap/
│   ├── main.tf
│   ├── provider.tf
│   ├── variable.tf
│   └── terraform.tfvars
│
├── child_module/
│   ├── azurerm_application_gateway/
│   ├── azurerm_bastion_host/
│   ├── azurerm_key_vault/
│   ├── azurerm_key_vault_role_assignment/
│   ├── azurerm_key_vault_secret/
│   ├── azurerm_linux_virtual_machine/
│   ├── azurerm_nat_gateway/
│   ├── azurerm_nat_gateway_public_ip_association/
│   ├── azurerm_network_interface/
│   ├── azurerm_network_security_group/
│   ├── azurerm_public_ip/
│   ├── azurerm_resource_group/
│   ├── azurerm_subnet/
│   ├── azurerm_subnet_nat_gateway_association/
│   ├── azurerm_subnet_network_security_group_association/
│   └── azurerm_virtual_network/
│
├── environments/
│   ├── pre-prod/
│   │   ├── backend.tf
│   │   ├── main.tf
│   │   ├── provider.tf
│   │   ├── variable.tf
│   │   └── terraform.tfvars
│   │
│   └── prod/
│
├── security_tool_reports/
│   ├── checkov/
│   ├── gitleaks/
│   ├── tflint/
│   ├── tfsec/
│   └── trivy/
│
├── .gitignore
└── README.md
🗄️ Terraform Remote Backend
Terraform uses an AzureRM Remote Backend instead of relying on local state.

Resource Group
      │
      ▼
rg-terraform-backend
      │
      ▼
Azure Storage Account
      │
      ▼
sttfstatekeshav27
      │
      ▼
Blob Container
      │
      ▼
tfstate
      │
      ▼
pre-prod.terraform.tfstate
Why Remote State?
☁️ Centralized Terraform state
🔒 State locking
🤝 Team collaboration
⚙️ GitHub Actions compatibility
💾 Protection against local state loss
🔄 Consistent state between local and CI/CD environments
🥾 Backend Bootstrap
A separate bootstrap/ Terraform configuration provisions the infrastructure required by the Terraform backend.

Bootstrap Terraform
        │
        ├── Resource Group
        │
        ├── Storage Account
        │
        └── Blob Container
                 │
                 ▼
          Terraform Remote State
The bootstrap process is handled through:

.github/workflows/terraform-bootstrap.yml
This solves the Terraform backend bootstrap dependency — the backend infrastructure must exist before the main Terraform configuration can use it.

🔐 GitHub Actions → Azure Authentication
Authentication is implemented using GitHub OIDC federation.

GitHub Repository
       │
       ▼
GitHub Actions
       │
       │ OIDC
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
The GitHub Actions identity receives only the Azure permissions required to deploy infrastructure, manage required RBAC assignments, and access Terraform state.

This eliminates the need to store an Azure client secret inside GitHub.

🔄 Terraform CI Pipeline
Workflow

.github/workflows/terraform-ci.yml
The CI pipeline validates infrastructure changes before they are merged.

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
Terraform Validation
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
This helps detect syntax issues, configuration problems, security misconfigurations, and exposed secrets before infrastructure changes reach main.

🚀 Terraform CD Pipeline
Workflow

.github/workflows/terraform-cd.yml
After validated infrastructure code reaches main, the CD workflow handles deployment.

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
Terraform Apply Job
 │
 ▼
Download Plan Artifact
 │
 ▼
Terraform Apply
 │
 ▼
☁️ Azure Infrastructure
The Terraform plan generated during the Plan job is stored as an artifact and downloaded by the Apply job so that the reviewed plan is the plan being applied.

🛡️ Security & Code Quality
Multiple security and code-quality tools are integrated into the CI process.

Tool	Purpose
🔍 TFLint	Terraform linting and configuration quality
🛡️ tfsec	Terraform security scanning
✅ Checkov	IaC policy and misconfiguration scanning
🔎 Trivy	Infrastructure-as-Code security scanning
🔑 Gitleaks	Detection of accidentally committed secrets
Security reports are maintained under:

security_tool_reports/
🌿 Git Branching Strategy
The repository follows a feature-branch based workflow with a protected main branch.

main
 │
 └────► feature/*
             │
             ▼
        Code Changes
             │
             ▼
          git add
             │
             ▼
         git commit
             │
             ▼
          git push
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
           Merge
             │
             ▼
        Terraform CD
Direct pushes to main are restricted using GitHub Branch Protection.

🧪 Idempotency Validation
After the initial infrastructure deployment, the Terraform CD pipeline was executed again without changing the infrastructure configuration.

Terraform returned:

No changes. Your infrastructure matches the configuration.
This validates that:

Terraform state matches the deployed Azure infrastructure
Remote state is working correctly
Re-running the same configuration does not unnecessarily recreate resources
🧹 Infrastructure Cleanup
A manually triggered Terraform destroy workflow is available for controlled cleanup of the environment.

terraform-destroy.yml
The workload infrastructure can therefore be destroyed through Terraform while keeping the separately managed backend infrastructure available for future deployments.

The destroy workflow is intended for controlled lab/environment cleanup and is not automatically triggered.

🔄 End-to-End DevOps Flow
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
┌───────────────────────┐
│     Terraform CI      │
│                       │
│ Validate              │
│ Lint                  │
│ Security Scan         │
│ Terraform Plan        │
└───────────┬───────────┘
            │
            ▼
       Code Review
            │
            ▼
        Merge → main
            │
            ▼
┌───────────────────────┐
│     Terraform CD      │
│                       │
│ OIDC Authentication   │
│ Terraform Init        │
│ Terraform Plan        │
│ Terraform Apply       │
└───────────┬───────────┘
            │
            ▼
      Microsoft Azure
            │
            ▼
     Landing Zone Infra
🧰 Technology Stack
☁️ Cloud	🏗️ IaC	⚙️ CI/CD	🔐 Identity	🛡️ Security
Microsoft Azure	Terraform	GitHub Actions	Microsoft Entra ID	Checkov
Azure Networking	AzureRM Provider	Git	OIDC Federation	tfsec
Azure Key Vault	Terraform Modules	GitHub	Azure RBAC	Trivy
Azure Storage	Remote State	YAML	Service Principal	Gitleaks
Azure Compute	State Locking	PR Workflow	Federated Credentials	TFLint
🎯 Key Learning Outcomes
This project demonstrates practical experience with:

Designing modular Terraform infrastructure
Managing Terraform Remote State in Azure
Solving the Terraform backend bootstrap problem
Implementing GitHub Actions CI/CD
Configuring GitHub OIDC federation with Azure
Implementing Azure RBAC for automation identities
Integrating IaC security scanning into CI
Working with protected branches and Pull Requests
Managing Terraform Plan → Apply workflows
Troubleshooting Azure authorization and RBAC issues
Validating Terraform infrastructure idempotency
🔮 Future Improvements
Potential improvements for the project include:

📐 Detailed Draw.io architecture diagram
🔒 Additional infrastructure security hardening
🏷️ Standardized Azure tagging strategy
🧪 Additional Terraform validation
👥 GitHub CODEOWNERS
🛡️ Additional branch protection policies
📊 Azure monitoring and diagnostic settings
💰 Cost-management controls
