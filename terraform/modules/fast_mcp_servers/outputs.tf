output "workweek_mcp_url" {
  value = google_cloud_run_v2_service.workweek_mcp_service.uri
}

output "serviceimmediately_mcp_url" {
  value = google_cloud_run_v2_service.serviceimmediately_mcp_service.uri
}
