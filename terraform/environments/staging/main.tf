# =============================================================================
# Project Elevate: Staging Environment Root Configuration
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "networking_security" {
  source      = "../../modules/networking_security"
  project_id  = var.project_id
  environment = var.environment
}

module "model_armor" {
  source      = "../../modules/model_armor"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
}

module "vertex_search" {
  source      = "../../modules/vertex_search"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
}

module "fast_mcp_servers" {
  source           = "../../modules/fast_mcp_servers"
  project_id       = var.project_id
  region           = var.region
  environment      = var.environment
  fastmcp_sa_email = module.networking_security.fastmcp_sa_email
}

module "agent_runtime" {
  source                     = "../../modules/agent_runtime"
  project_id                 = var.project_id
  region                     = var.region
  environment                = var.environment
  agent_sa_email             = module.networking_security.agent_sa_email
  gemini_model               = var.gemini_model
  workweek_mcp_url           = module.fast_mcp_servers.workweek_mcp_url
  serviceimmediately_mcp_url = module.fast_mcp_servers.serviceimmediately_mcp_url
}
