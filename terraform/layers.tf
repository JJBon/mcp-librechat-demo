resource "null_resource" "install_dependencies" {
  triggers = {
    requirements = filesha256("${path.module}/../lambda/dcr/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<EOT
      rm -rf ${path.module}/layer_build
      mkdir -p ${path.module}/layer_build/python
      pip install -r ${path.module}/../lambda/dcr/requirements.txt -t ${path.module}/layer_build/python --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --only-binary=:all: --upgrade
    EOT
  }
}

data "archive_file" "layer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/layer_build"
  output_path = "${path.module}/dcr_layer.zip"
  depends_on  = [null_resource.install_dependencies]
}

resource "aws_lambda_layer_version" "dcr_dependencies" {
  filename            = data.archive_file.layer_zip.output_path
  layer_name          = "${var.app_name}-dcr-dependencies"
  compatible_runtimes = ["python3.12"]
  source_code_hash    = data.archive_file.layer_zip.output_base64sha256
}
