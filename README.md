# Apnea Detection Kubernetes & GitOps Pipeline

![Terraform](https://img.shields.io/badge/terraform-%235835CC.svg?style=for-the-badge&logo=terraform&logoColor=white)
![AWS EKS](https://img.shields.io/badge/AWS_EKS-%23FF9900.svg?style=for-the-badge&logo=amazonaws&logoColor=white)
![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?style=for-the-badge&logo=kubernetes&logoColor=white)
![ArgoCD](https://img.shields.io/badge/ArgoCD-%23EF7B4D.svg?style=for-the-badge&logo=argo&logoColor=white)
![Vault](https://img.shields.io/badge/Vault-%23000000.svg?style=for-the-badge&logo=vault&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=Prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/grafana-%23F46800.svg?style=for-the-badge&logo=grafana&logoColor=white)

## Final Application Result

<img width="3423" height="1758" alt="Screenshot from 2026-06-05 21-18-33" src="https://github.com/user-attachments/assets/1c0656cd-44bd-45e6-9bc5-a0b4831d8058" />
## Technical Project Overview

This project demonstrates an enterprise-grade, highly available MLOps lifecycle for a clinical sleep apnea diagnostic tool. It transitions the application from a traditional instance-based deployment to a fully orchestrated **Kubernetes (EKS)** environment. 

By implementing the **GitOps** methodology, Infrastructure-as-Code (IaC), and a comprehensive observability stack, this pipeline ensures that the deep learning inference engine (FastAPI) and interactive frontend (Streamlit) are resilient, self-healing, and continuously synchronized with the source repository.

## GitOps & Automation Workflow

The architecture utilizes a decoupled CI/CD pattern to completely separate continuous integration from continuous deployment, ensuring maximum security and state consistency:

* **Zero-Trust Secrets (HashiCorp Vault):** All AWS credentials and deployment tokens are completely removed from GitHub. The CI workflow authenticates via a machine-identity `AppRole` to dynamically fetch short-lived access keys.
* **Immutable Infrastructure (Terraform):** Defines the underlying AWS environment. It automatically provisions a multi-AZ VPC and the managed EKS Control Plane, deploying memory-optimized `t3.medium` worker nodes.
* **Continuous Integration (GitHub Actions):** Automates the testing, building, and packaging of the Python application containers upon every repository push.
* **Artifact Management (Sonatype Nexus):** Built containers and heavy PyTorch model weights are securely pushed to a private Nexus registry, bypassing standard Docker Hub limits and ensuring tight access control.
* **Continuous Deployment (ArgoCD):** Acts as the GitOps controller inside the EKS cluster. It continuously monitors the repository's `k8s/` manifests and automatically pulls state changes, instantly self-healing the infrastructure if live pods drift from the code.

<img width="3237" height="1125" alt="Screenshot from 2026-06-05 21-17-16" src="https://github.com/user-attachments/assets/d0166831-e00d-4d3f-a727-c11c85b62cd0" />
<img width="3502" height="1762" alt="Screenshot from 2026-06-05 21-16-38" src="https://github.com/user-attachments/assets/53551299-3be5-4b0b-982a-82523f9607ff" />

## Infrastructure & Observability Deep Dive

A production AI system requires constant monitoring to track inference latency, hardware utilization, and potential bottlenecks. This deployment leverages the **"App of Apps"** GitOps pattern to inject a full enterprise monitoring suite:

* **Metrics Scraping (Prometheus):** Deployed via Helm through ArgoCD, bypassing EKS CRD limits using Server-Side Apply. It continuously scrapes CPU, RAM, and network metrics from the EC2 worker nodes and inference pods.
* **Hardware Telemetry (Node Exporters):** DaemonSets automatically deploy to every AWS worker node to expose deep system-level metrics directly to Prometheus.
* **Data Visualization (Grafana):** Connects directly to the Prometheus database to build centralized, dark-mode visual dashboards for real-time

<img width="3560" height="1798" alt="Screenshot from 2026-06-05 21-15-48" src="https://github.com/user-attachments/assets/9e1abccc-299d-4b9d-bc03-d1ee3eafeb32" />

## Repository Structure

```text
apnea-k8s-migration/
├── .github/workflows/         # CI/CD pipeline definitions
│   └── ci.yml                 # Automated GitHub Actions workflow (Build & EKS Deploy)
├── app/                       # Application & Model source code
│   ├── dashboard.py           # Streamlit UI for dynamic signal upload
│   ├── main.py                # FastAPI backend endpoints
│   ├── model.py               # PyTorch ML Diagnostic logic
│   ├── Dockerfile             # Production container build
│   └── requirements.txt       # Pinned Python dependencies 
├── infrastructure/            # Terraform IaC definitions
│   ├── main.tf                # EKS Cluster, VPC, and S3 Bucket
│   ├── variables.tf           # Environment & IP configuration
│   ├── outputs.tf             # Dynamic state outputs 
│   ├── providers.tf           # AWS provider & Vault integration
│   └── .terraform.lock.hcl    # Terraform dependency lockfile
├── k8s/                       # Kubernetes GitOps Manifests
│   ├── apnea-app.yaml         # Deployment, Service, and ConfigMap for the app
│   ├── argocd-apnea-app.yaml  # ArgoCD application definition for the API
│   ├── argocd-plg-stack.yaml  # ArgoCD Helm definition for the PL Observability stack
│   └── nexus-values.yaml      # Custom Helm values for Sonatype Nexus artifact registry
├── .dockerignore              # Docker build exclusions
├── .gitignore                 # Git tracking exclusions
└── README.md                  # Project documentation
