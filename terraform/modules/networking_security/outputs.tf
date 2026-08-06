output "agent_sa_email" {
  description = "Email of the Agent Runtime Service Account"
  value       = google_service_account.agent_sa.email
}

output "fastmcp_sa_email" {
  description = "Email of the FastMCP Service Account"
  value       = google_service_account.fastmcp_sa.email
}

output "mcp_token_secret_id" {
  description = "Resource ID of the MCP token in Secret Manager"
  value       = google_secret_manager_secret.mcp_token_secret.id
}
