# Security group rules for direct access to inspector (when debugging)
# These rules allow public access to port 8080 when assign_public_ip is true

resource "aws_vpc_security_group_ingress_rule" "inspector_direct_proxy" {
  count = var.assign_public_ip ? 1 : 0

  security_group_id = var.inspector_security_group_id

  description = "Allow public access to nginx proxy port (debugging)"
  from_port   = 8080
  to_port     = 8080
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "${var.environment}-inspector-proxy-public"
  }
}
