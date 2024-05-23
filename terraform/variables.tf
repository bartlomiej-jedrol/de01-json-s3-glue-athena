variable "raw_bucket" {
  type    = string
  default = "de01-raw-data"
}

variable "processed_bucket" {
  type    = string
  default = "de01-processed-data"
}

variable "lambda_ecr_repo" {
  type    = string
  default = "de01-lambda-repo"
}

variable "lambda_iam_role" {
  type    = string
  default = "de01-lambda-role"
}
