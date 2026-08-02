# 🚀 Azure Landing Zone Deployment using Terraform

## 📌 Project Overview

This project provides a production-ready **Azure Landing Zone** built using **Terraform**. It follows Infrastructure as Code (IaC) best practices and uses a modular architecture to deploy Azure resources in a secure, scalable, and reusable manner.

The objective of this project is to automate the provisioning of Azure infrastructure while maintaining consistency, security, and ease of management across different environments.

---

## ✨ Features

* Modular Terraform Architecture
* Environment-based deployment (Dev / Non-Prod / Prod)
* Reusable Child Modules
* Secure Infrastructure Design
* Easy to Customize and Extend
* Infrastructure as Code (IaC)
* Production-ready Project Structure

---

## 🏗️ Resources Deployed

The project includes Terraform modules for deploying the following Azure resources:

* Resource Group
* Virtual Network (VNet)
* Subnet
* Network Security Group (NSG)
* Network Interface (NIC)
* Azure Bastion Host
* Azure Container Registry (ACR)
* Azure Kubernetes Service (AKS)
* Storage Account
* Storage Container
* Virtual Machine (VM)

---

## 📁 Project Structure

```text
Terraform/
│
├── child_module/
│   ├── resource_group/
│   ├── virtual_network/
│   ├── subnet/
│   ├── network_security_group/
│   ├── Network_interface/
│   ├── Bastion_host/
│   ├── storage_account/
│   ├── storage_container/
│   ├── acr_registry/
│   ├── kubernetes_service/
│   └── virtual_machine/
│
└── environment/
    ├── dev/
    ├── no-prod/
    └── prod/
```

---

## ⚙️ Prerequisites

Before deploying this project, ensure the following tools are installed:

* Terraform
* Azure CLI
* Git
* Visual Studio Code (Recommended)

---

## 🚀 Deployment Steps

### Clone the Repository

```bash
git clone https://github.com/adityap1singh/Azure-Landing-zone.git
```

### Navigate to Environment

```bash
cd Terraform/environment/dev
```

### Initialize Terraform

```bash
terraform init
```

### Validate Configuration

```bash
terraform validate
```

### Review Execution Plan

```bash
terraform plan
```

### Deploy Infrastructure

```bash
terraform apply
```

---

## 🔒 Security Best Practices

This project follows Azure security recommendations by implementing:

* Modular Infrastructure Design
* Least Privilege Principle
* Network Segmentation
* Secure Resource Provisioning
* Environment Isolation
* Infrastructure as Code Best Practices

---

## 🌍 Supported Environments

* Development
* Non-Production
* Production

Each environment can have its own configuration using separate Terraform variable files.

---

## 🛠️ Technologies Used

* Terraform
* Microsoft Azure
* Azure Resource Manager (ARM)
* Azure CLI
* Git
* GitHub

---

## 🎯 Future Enhancements

Planned improvements include:

* GitHub Actions CI/CD Pipeline
* Terraform Remote Backend
* Azure Key Vault Integration
* Private Endpoints
* Monitoring with Azure Monitor
* Log Analytics Workspace
* Application Gateway
* Load Balancer
* Azure Firewall
* Diagnostic Settings
* Policy as Code
* Cost Optimization
* Security Scanning (Checkov, TFLint, Trivy)
* Multi-region Deployment

---

## 🤝 Contribution

Contributions, suggestions, and improvements are welcome. Feel free to fork this repository, create a feature branch, and submit a pull request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

**Aditya Singh**

Cloud & DevOps Engineer

**GitHub:** https://github.com/adityap1singh

---

⭐ If you find this project useful, don't forget to **Star** the repository!
