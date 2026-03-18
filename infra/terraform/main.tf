terraform {
	required_version = ">= 1.5.0"

	required_providers {
		aws = {
			source  = "hashicorp/aws"
			version = "~> 5.0"
		}
	}
}

provider "aws" {
	region = var.aws_region
}

locals {
	instance_name     = "${var.project_name}-${var.environment}"
	generated_keyname = "${local.instance_name}-key"
	common_tags = merge(
		{
			Project     = var.project_name
			Environment = var.environment
			ManagedBy   = "terraform"
		},
		var.tags
	)
}

resource "aws_lightsail_key_pair" "generated" {
	count      = var.ssh_key_pair_name == "" && var.ssh_public_key != "" ? 1 : 0
	name       = local.generated_keyname
	public_key = var.ssh_public_key
}

resource "aws_lightsail_instance" "app" {
	name              = local.instance_name
	availability_zone = var.availability_zone
	blueprint_id      = var.lightsail_blueprint_id
	bundle_id         = var.lightsail_bundle_id
	key_pair_name = var.ssh_key_pair_name != "" ? var.ssh_key_pair_name : (
		length(aws_lightsail_key_pair.generated) > 0 ? aws_lightsail_key_pair.generated[0].name : null
	)

	user_data = <<-EOT
		#!/bin/bash
		set -euo pipefail
		apt-get update
		apt-get install -y ca-certificates curl gnupg lsb-release

		install -m 0755 -d /etc/apt/keyrings
		curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
		chmod a+r /etc/apt/keyrings/docker.gpg

		echo \
			"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
			$(. /etc/os-release && echo $VERSION_CODENAME) stable" \
			| tee /etc/apt/sources.list.d/docker.list > /dev/null

		apt-get update
		apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
		usermod -aG docker ubuntu

		mkdir -p /opt/${var.project_name}
	EOT

	tags = local.common_tags
}

resource "aws_lightsail_instance_public_ports" "ports" {
	instance_name = aws_lightsail_instance.app.name

	port_info {
		from_port = 22
		to_port   = 22
		protocol  = "tcp"
	}

	port_info {
		from_port = 80
		to_port   = 80
		protocol  = "tcp"
	}

	port_info {
		from_port = 443
		to_port   = 443
		protocol  = "tcp"
	}
}

resource "aws_lightsail_static_ip" "app" {
	count = var.create_static_ip ? 1 : 0
	name  = "${local.instance_name}-ip"
}

resource "aws_lightsail_static_ip_attachment" "app" {
	count         = var.create_static_ip ? 1 : 0
	static_ip_name = aws_lightsail_static_ip.app[0].name
	instance_name  = aws_lightsail_instance.app.name
}
