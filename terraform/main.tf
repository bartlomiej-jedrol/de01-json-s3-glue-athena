terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "bj-terraform-states"
    key     = "state-de01-json-s3-glue-athena/terraform.tfstate"
    region  = "eu-central-1"
    encrypt = true
  }
}

provider "aws" {
  region = "eu-central-1"
}

# S3 buckets
resource "aws_s3_bucket" "raw_bucket" {
  bucket = var.raw_bucket
}

resource "aws_s3_bucket" "processed_bucket" {
  bucket = var.processed_bucket
}

resource "aws_s3_bucket" "athena_results" {
  bucket = var.athena_results
}

#ECR repository
resource "aws_ecr_repository" "ecr-repo" {
  name = var.lambda_ecr_repo
}

# Lambda
resource "aws_iam_role" "lambda_iam_role" {
  name = var.lambda_iam_role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })

  managed_policy_arns = ["arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess", "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole", "arn:aws:iam::aws:policy/AmazonS3FullAccess"]
}

resource "aws_lambda_function" "de01_lambda" {
  function_name = "de01_lambda"
  timeout       = 10
  image_uri     = "${aws_ecr_repository.ecr-repo.repository_url}:latest"
  package_type  = "Image"

  role = aws_iam_role.lambda_iam_role.arn

  environment {
    variables = {
      S3_TARGET_BUCKET = var.processed_bucket
    }
  }
}

resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.de01_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${aws_s3_bucket.raw_bucket.id}"
}

resource "aws_s3_bucket_notification" "lambda_notification" {
  bucket = aws_s3_bucket.raw_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.de01_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }
}

# SQS queue
resource "aws_sqs_queue" "sqs_queue" {
  name = var.sqs_queue
}

# Defines who can access your queue
resource "aws_sqs_queue_policy" "sqs_policy" {
  queue_url = aws_sqs_queue.sqs_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.sqs_queue.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" : aws_s3_bucket.processed_bucket.arn
          }
        }
      },
    ]
  })
}

resource "aws_s3_bucket_notification" "sqs_notification" {
  bucket = aws_s3_bucket.processed_bucket.id

  queue {
    queue_arn = aws_sqs_queue.sqs_queue.arn
    events    = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
  }
}

# Glue
resource "aws_iam_role" "glue_iam_role" {
  name = var.glue_iam_role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      },
    ]
  })

  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"]
}

resource "aws_iam_role_policy" "glue-inline-policy" {
  name = var.glue_inline_policy
  role = aws_iam_role.glue_iam_role.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:Get*",
          "s3:List*"
        ]
        Resource = [
          "arn:aws:s3:::de01-processed-data", "arn:aws:s3:::de01-processed-data/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:DeleteMessage",
          "sqs:GetQueueUrl",
          "sqs:ListDeadLetterSourceQueues",
          "sqs:DeleteMessageBatch",
          "sqs:ReceiveMessage",
          "sqs:GetQueueAttributes",
          "sqs:ListQueueTags",
          "sqs:SetQueueAttributes",
          "sqs:PurgeQueue",
        ]
        Resource = [aws_sqs_queue.sqs_queue.arn]
      }
    ],
  })
}
