variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "backend_task_role_name" {
  description = "Name of the backend ECS task role to attach PutObject/DeleteObject policy to."
  type        = string
}

variable "imgproxy_task_role_name" {
  description = "Name of the imgproxy ECS task role to attach GetObject policy to. Empty string skips the attachment."
  type        = string
  default     = ""
}

variable "cors_allowed_origins" {
  description = "Origins allowed in S3 CORS rule. Direct uploads currently go through the backend, but keeping this open allows future pre-signed PUT support."
  type        = list(string)
  default     = ["https://myvoya.ai", "https://www.myvoya.ai", "https://staging.myvoya.ai"]
}

variable "tags" {
  description = "Tags to apply to resources."
  type        = map(string)
  default     = {}
}
