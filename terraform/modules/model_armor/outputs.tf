output "armor_audit_bucket_name" {
  value = google_storage_bucket.armor_audit_logs.name
}

output "armor_telemetry_dataset_id" {
  value = google_bigquery_dataset.model_armor_telemetry.dataset_id
}
