# =============================================================================
# Terraform Module: Google Cloud Model Armor (Safety & Guardrails)
# =============================================================================

# Google Cloud Storage bucket for Model Armor audit logs and compliance records
resource "google_storage_bucket" "armor_audit_logs" {
  name          = "${var.project_id}-${var.environment}-armor-audit-logs"
  location      = var.region
  project       = var.project_id
  force_destroy = var.environment == "dev" ? true : false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = var.environment == "prod" ? 365 : 30
    }
    action {
      type = "Delete"
    }
  }
}

# BigQuery Dataset for Anonymized Model Armor Inspection Telemetry
resource "google_bigquery_dataset" "model_armor_telemetry" {
  dataset_id  = "${var.environment}_model_armor_telemetry"
  project     = var.project_id
  location    = var.region
  description = "Project Elevate: Model Armor safety inspection logs & anonymized metrics"

  labels = {
    env = var.environment
    app = "project-elevate"
  }
}
