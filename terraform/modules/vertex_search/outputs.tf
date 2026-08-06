output "policy_docs_bucket_name" {
  value = google_storage_bucket.policy_docs_bucket.name
}

output "data_store_id" {
  value = google_discovery_engine_data_store.hr_policy_datastore.data_store_id
}

output "search_engine_id" {
  value = google_discovery_engine_search_engine.hr_policy_search_engine.engine_id
}
