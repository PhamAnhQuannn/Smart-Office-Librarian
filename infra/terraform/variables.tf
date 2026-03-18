variable "aws_region" {
	description = "AWS region for Lightsail resources."
	type        = string
	default     = "us-east-1"
}

variable "project_name" {
	description = "Project name used for resource naming."
	type        = string
	default     = "embedlyzer"
}

variable "environment" {
	description = "Deployment environment name (dev, staging, prod)."
	type        = string
	default     = "prod"
}

variable "availability_zone" {
	description = "AWS availability zone for Lightsail instance."
	type        = string
	default     = "us-east-1a"
}

variable "lightsail_bundle_id" {
	description = "Lightsail instance bundle id."
	type        = string
	default     = "medium_2_0"
}

variable "lightsail_blueprint_id" {
	description = "Lightsail blueprint for base OS image."
	type        = string
	default     = "ubuntu_22_04"
}

variable "ssh_key_pair_name" {
	description = "Existing Lightsail key pair name. Leave empty to create from ssh_public_key."
	type        = string
	default     = ""
}

variable "ssh_public_key" {
	description = "Public key to create a Lightsail key pair when ssh_key_pair_name is empty."
	type        = string
	default     = ""
}

variable "create_static_ip" {
	description = "Whether to allocate and attach a static IP."
	type        = bool
	default     = true
}

variable "tags" {
	description = "Additional tags applied to all resources."
	type        = map(string)
	default     = {}
}
