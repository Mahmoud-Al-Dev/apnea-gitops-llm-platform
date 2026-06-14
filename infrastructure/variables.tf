variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "project_name" {
  type    = string
  default = "apnea-api"
}

variable "ecr_repo_name" {
  type    = string
  default = "apnea-api"
}

variable "container_port" {
  type    = number
  default = 8000
}

# Optional: restrict SSH to your public IP/32. Leave "" to disable SSH.
variable "ssh_cidrs" {
  type        = list(string)
  description = "List of IPs allowed to SSH into the EC2 instance"
  default     = [] # Completely empty and safe for public GitHub!
}

variable "instance_type" {
  type    = string
  default = "t3.medium"
}

