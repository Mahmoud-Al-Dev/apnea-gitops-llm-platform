output "cluster_name" {
  value       = module.eks.cluster_name
  description = "The name of the EKS cluster to pass to the aws cli command"
}

output "cluster_endpoint" {
  value       = module.eks.cluster_endpoint
  description = "The endpoint URL for your Kubernetes API server"
}

output "weights_bucket_name" {
  value       = aws_s3_bucket.ml_weights.id
  description = "The name of the S3 bucket created for ML weights"
}

output "ecr_registry_url" {
  value       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
  description = "The URL of the AWS ECR registry"
}