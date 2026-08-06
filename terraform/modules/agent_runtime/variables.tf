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

variable "agent_sa_email" {
  type = string
}

variable "gemini_model" {
  type    = string
  default = "gemini-2.5-flash"
}

variable "agent_image" {
  type    = string
  default = "gcr.io/gcp-elevate-prod/elevate-supervisor-agent:latest"
}

variable "workweek_mcp_url" {
  type = string
}

variable "serviceimmediately_mcp_url" {
  type = string
}
