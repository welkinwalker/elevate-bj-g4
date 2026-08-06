variable "project_id" {
  type    = string
  default = "gcp-elevate-prod"
}

variable "primary_region" {
  type    = string
  default = "us-central1"
}

variable "secondary_region" {
  type    = string
  default = "us-east4"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "gemini_model" {
  type    = string
  default = "gemini-3.5-flash"
}
