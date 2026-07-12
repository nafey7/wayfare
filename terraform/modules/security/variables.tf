# Security Module Variables

variable "environment" {
  description = "Environment name (e.g., staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "mongodb_cidr" {
  description = "CIDR block for MongoDB Atlas VPC peering"
  type        = string
  default     = "192.168.248.0/21"
}

variable "enable_vpc_endpoints" {
  description = "Enable security groups for VPC endpoints"
  type        = bool
  default     = true
}

variable "enable_strapi_rds" {
  description = "Enable security group for Strapi RDS PostgreSQL"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
