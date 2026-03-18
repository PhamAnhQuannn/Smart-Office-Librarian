output "instance_name" {
	description = "Lightsail instance name."
	value       = aws_lightsail_instance.app.name
}

output "instance_arn" {
	description = "Lightsail instance ARN."
	value       = aws_lightsail_instance.app.arn
}

output "instance_public_ip" {
	description = "Public IP used by the deployment."
	value = var.create_static_ip ? aws_lightsail_static_ip.app[0].ip_address : aws_lightsail_instance.app.public_ip_address
}

output "static_ip_name" {
	description = "Attached static IP resource name when create_static_ip is true."
	value       = var.create_static_ip ? aws_lightsail_static_ip.app[0].name : null
}
