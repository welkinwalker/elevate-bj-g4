variable "project_id" {
  type    = string
  default = "gcp-elevate-staging"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "environment" {
  type    = string
  default = "staging"
}

variable "gemini_model" {
  type    = string
  default = "gemini-2.5-flash"
}
