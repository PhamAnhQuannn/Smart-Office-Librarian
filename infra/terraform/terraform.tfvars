aws_region             = "us-east-1"
project_name           = "embedlyzer"
environment            = "prod"
availability_zone      = "us-east-1a"
lightsail_bundle_id    = "medium_2_0"
lightsail_blueprint_id = "ubuntu_22_04"

# New key pair will be created from the public key below
ssh_key_pair_name = ""
ssh_public_key    = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIN5J6gibE72eYjVWiHPEUKuah3Y49RNncEOWja242/zh embedlyzer-prod"

create_static_ip = true

tags = {
  Owner      = "engineering"
  CostCenter = "platform"
  Compliance = "mvp"
}
