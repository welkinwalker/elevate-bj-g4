# =============================================================================
# Terraform Module: FastMCP Enterprise Cloud Run Microservices
# =============================================================================

# Cloud Run Service: WorkWeek FastMCP Server
resource "google_cloud_run_v2_service" "workweek_mcp_service" {
  name     = "${var.environment}-workweek-mcp-server"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.fastmcp_sa_email

    scaling {
      min_instance_count = var.environment == "prod" ? 1 : 0
      max_instance_count = 100
    }

    containers {
      image = var.workweek_image

      resources {
        limits = {
          cpu    = "1000m"
          memory = "1024Mi"
        }
      }

      env {
        name  = "PORT"
        value = "8080"
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "MCP_PATH"
        value = "/work-week/mcp/"
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Cloud Run Service: ServiceImmediately FastMCP Server
resource "google_cloud_run_v2_service" "serviceimmediately_mcp_service" {
  name     = "${var.environment}-serviceimmediately-mcp-server"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.fastmcp_sa_email

    scaling {
      min_instance_count = var.environment == "prod" ? 1 : 0
      max_instance_count = 100
    }

    containers {
      image = var.serviceimmediately_image

      resources {
        limits = {
          cpu    = "1000m"
          memory = "1024Mi"
        }
      }

      env {
        name  = "PORT"
        value = "8080"
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "MCP_PATH"
        value = "/service-immediately/mcp/"
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}
