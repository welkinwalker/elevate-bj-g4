variable "project_id" {
  type    = string
  default = "gcp-elevate-dev"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "gemini_model" {
  type    = string
  default = "gemini-2.5-flash"
}
