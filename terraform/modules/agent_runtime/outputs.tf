output "agent_runtime_service_url" {
  value = google_cloud_run_v2_service.agent_runtime_service.uri
}
