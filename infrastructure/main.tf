data "aws_caller_identity" "current" {}

data "vault_generic_secret" "aws_creds" {
  path = "secret/aws"
}

locals {
  cluster_name = "${var.project_name}-eks-cluster"
}

# ------------------------------------------------------------------
# 🌐 Upgraded Networking Layer (Multi-AZ VPC for EKS)
# ------------------------------------------------------------------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc"
  cidr = "10.10.0.0/16"

  # EKS requires at least 2 Availability Zones
  azs             = ["eu-central-1a", "eu-central-1b"]
  public_subnets  = ["10.10.1.0/24", "10.10.2.0/24"]
  private_subnets = ["10.10.11.0/24", "10.10.12.0/24"]

  # One NAT Gateway to save costs during short testing blocks
  enable_nat_gateway = true
  single_nat_gateway = true

  # Crucial tags so EKS knows how to discover load balancers
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

# ------------------------------------------------------------------
# ☸️ Amazon EKS Cluster & Managed Worker Nodes
# ------------------------------------------------------------------
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = local.cluster_name
  cluster_version = "1.30"

  cluster_endpoint_public_access = true

  # --------------------------------------------------------
  # Disable Enterprise Logging & KMS to save budget
  # --------------------------------------------------------
  create_kms_key              = false
  cluster_encryption_config   = {}
  create_cloudwatch_log_group = false
  # --------------------------------------------------------

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    app_nodes = {
      min_size     = 1
      max_size     = 2
      desired_size = 2

      instance_types = ["t3.large"]
      capacity_type  = "ON_DEMAND"

      iam_role_additional_policies = {
        AmazonEC2ContainerRegistryReadOnly = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
        AmazonS3ReadOnlyAccess             = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
      }
    }
  }

  tags = {
    Environment = "production-test"
    Project     = var.project_name
  }
}

# ------------------------------------------------------------------
# S3 Bucket for ML Weights 
# ------------------------------------------------------------------
resource "aws_s3_bucket" "ml_weights" {
  bucket = "${var.project_name}-ml-weights-${data.aws_caller_identity.current.account_id}"
}