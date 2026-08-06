variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "environment" {
  type = string
}

variable "fastmcp_sa_email" {
  type = string
}

variable "workweek_image" {
  type    = string
  default = "gcr.io/gcp-elevate-prod/workweek-mcp:latest"
}

variable "serviceimmediately_image" {
  type    = string
  default = "gcr.io/gcp-elevate-prod/serviceimmediately-mcp:latest"
}
