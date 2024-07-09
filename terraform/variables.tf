variable "raw_bucket" {
  type    = string
  default = "de01-raw-data"
}

variable "processed_bucket" {
  type    = string
  default = "de01-processed-data"
}

variable "aggregated_bucket" {
  type    = string
  default = "de01-aggregated-data"
}

variable "lambda_ecr_repo" {
  type    = string
  default = "de01-lambda-repo"
}

variable "lambda_iam_role" {
  type    = string
  default = "de01-lambda-role"
}

variable "athena_results" {
  type    = string
  default = "de01-athena-results"
}

variable "sqs_queue" {
  type    = string
  default = "de01-sqs-queue"
}

variable "glue_iam_role" {
  type    = string
  default = "de01-glue-role"
}

variable "glue_inline_policy" {
  type    = string
  default = "de01-glue-inline-policy"
}
