resource "aws_ecr_repository" "this" {
  name = "${var.project_name}-lambdas"
}

data "aws_region" "current" {}

#resource "null_resource" "build_and_push" {
#provisioner "local-exec" {
#command = <<EOT
#aws ecr get-login-password --region ${data.aws_region.current.name} \
#| docker login --username AWS --password-stdin ${aws_ecr_repository.this.repository_url}
#docker build --platform linux/amd64 -t ${var.project_name}-lambda ./lambdas
#docker tag ${var.project_name}-lambda:latest ${aws_ecr_repository.this.repository_url}:latest
#docker push ${aws_ecr_repository.this.repository_url}:latest
#EOT
#}
#depends_on = [aws_ecr_repository.this]
#}
resource "null_resource" "build_and_push" {
  provisioner "local-exec" {
    command = <<EOT
source ./build-and-push.sh
EOT
  }
  depends_on = [aws_ecr_repository.this]
}


data "aws_ecr_image" "latest" {
  repository_name = aws_ecr_repository.this.name
  image_tag       = "latest"
  depends_on      = [null_resource.build_and_push]
}

locals {
  image_uri = "${aws_ecr_repository.this.repository_url}@${data.aws_ecr_image.latest.image_digest}"
}
