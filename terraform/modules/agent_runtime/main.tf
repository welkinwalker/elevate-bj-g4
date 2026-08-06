# =============================================================================
# Terraform Module: Agent Platform Agent Runtime & Supervisor Agent
# =============================================================================

resource "google_cloud_run_v2_service" "agent_runtime_service" {
  name     = "${var.environment}-elevate-supervisor-agent"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.agent_sa_email

    scaling {
      min_instance_count = var.environment == "prod" ? 2 : 0
      max_instance_count = 50
    }

    containers {
      image = var.agent_image

      resources {
        limits = {
          cpu    = "2000m"
          memory = "2048Mi"
        }
      }

      env {
        name  = "PORT"
        value = "8080"
      }
      env {
        name  = "APP_NAME"
        value = "elevate-hr-agent"
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "GEMINI_MODEL"
        value = var.gemini_model
      }
      env {
        name  = "WORKWEEK_MCP_URL"
        value = var.workweek_mcp_url
      }
      env {
        name  = "SERVICEIMMEDIATELY_MCP_URL"
        value = var.serviceimmediately_mcp_url
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "VERTEX_AI_SEARCH_LOCATION"
        value = "global"
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}
