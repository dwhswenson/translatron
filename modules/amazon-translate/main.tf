resource "aws_iam_policy" "this" {
  name = "${var.project_name}-language-detect-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "comprehend:DetectDominantLanguage",
        "translate:TranslateText"
      ]
      Resource = "*"
    }]
  })
}

resource "aws_iam_policy_attachment" "this" {
  name       = "${var.project_name}-language-detect-attach"
  roles      = [var.lambda_role_name]
  policy_arn = aws_iam_policy.this.arn
}
