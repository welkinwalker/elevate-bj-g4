# =============================================================================
# Terraform Module: Networking & Security
# =============================================================================

# Service Account for Agent Runtime
resource "google_service_account" "agent_sa" {
  project      = var.project_id
  account_id   = "${var.environment}-elevate-agent-sa"
  display_name = "Project Elevate Agent Runtime Service Account (${var.environment})"
}

# Service Account for FastMCP Cloud Run services
resource "google_service_account" "fastmcp_sa" {
  project      = var.project_id
  account_id   = "${var.environment}-fastmcp-sa"
  display_name = "FastMCP Enterprise Cloud Run Service Account (${var.environment})"
}

# IAM Permissions for Agent SA
resource "google_project_iam_member" "agent_vertex_user" {
  project = var.project_id
  role    = "roles/discoveryengine.editor"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "agent_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

# Secret Manager Secret for MCP Access Token
resource "google_secret_manager_secret" "mcp_token_secret" {
  project   = var.project_id
  secret_id = "${var.environment}-mcp-access-token"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "mcp_token_version" {
  secret      = google_secret_manager_secret.mcp_token_secret.id
  secret_data = var.mcp_token_value
}

resource "google_secret_manager_secret_iam_member" "agent_secret_accessor" {
  secret_id = google_secret_manager_secret.mcp_token_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_sa.email}"
}
