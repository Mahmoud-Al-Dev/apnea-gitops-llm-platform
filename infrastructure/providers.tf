terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "apnea-mlops-state-mahmoud123321" 
    key            = "terraform.tfstate"         # The name of the file inside the bucket
    region         = "eu-central-1"
    encrypt        = true                        # AES-256 encryption at rest
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    vault= {
      source  = "hashicorp/vault"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region     = var.aws_region
  access_key = data.vault_generic_secret.aws_creds.data["access_key"]
  secret_key = data.vault_generic_secret.aws_creds.data["secret_key"]
}

provider "vault" {
  address   = "https://vault-cluster-public-vault-8c7a912a.0a2ef11a.z1.hashicorp.cloud:8200"
  namespace = "admin" 
  skip_child_token = true
}