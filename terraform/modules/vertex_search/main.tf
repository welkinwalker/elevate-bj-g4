# =============================================================================
# Terraform Module: Vertex AI Search RAG & Policy Knowledge Base
# =============================================================================

# Cloud Storage Bucket for HR Policy Document Repository
resource "google_storage_bucket" "policy_docs_bucket" {
  name          = "${var.project_id}-${var.environment}-hr-policies-source"
  location      = var.region
  project       = var.project_id
  force_destroy = var.environment == "dev" ? true : false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

# Discovery Engine Data Store for Static Policy Document Search
resource "google_discovery_engine_data_store" "hr_policy_datastore" {
  project                     = var.project_id
  location                    = "global"
  data_store_id               = "${var.environment}-hr-policies-store"
  display_name                = "Project Elevate HR Policies Data Store (${var.environment})"
  industry_vertical           = "GENERIC"
  content_config              = "CONTENT_REQUIRED"
  solution_types              = ["SOLUTION_TYPE_SEARCH"]
  create_advanced_site_search = false
}

# Discovery Engine Search Engine / App
resource "google_discovery_engine_search_engine" "hr_policy_search_engine" {
  project        = var.project_id
  location       = "global"
  engine_id      = "${var.environment}-hr-policies-engine"
  collection_id  = "default_collection"
  display_name   = "Project Elevate Policy Search Engine (${var.environment})"
  data_store_ids = [google_discovery_engine_data_store.hr_policy_datastore.data_store_id]

  search_engine_config {
    search_tier = "SEARCH_TIER_ENTERPRISE"
  }
}
