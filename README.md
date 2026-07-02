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

<img width="3599" height="1755" alt="Screenshot from 2026-06-14 22-37-26" src="https://github.com/user-attachments/assets/9ced24f8-e4ad-4995-adcf-4196aacf99dd" /><img width="3276" height="1953" alt="Screenshot from 2026-06-14 22-49-17" src="https://github.com/user-attachments/assets/6854239d-1fe4-48f9-af4a-7d5a782b41d7" />


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
