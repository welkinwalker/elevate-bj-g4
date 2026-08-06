variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "environment" {
  description = "Target environment (dev, staging, prod)"
  type        = string
}

variable "mcp_token_value" {
  description = "Secret Personal Access Token for FastMCP services"
  type        = string
  sensitive   = true
  default     = "mcp_default_secret_pat"
}
