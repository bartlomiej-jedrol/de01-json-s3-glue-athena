AWS_ACCOUNT_ID ?=
AWS_REGION ?=
AWS_ECR_REPO = "de01-lambda-repo"
AWS_LAMBDA_FUNCTION = "de01_lambda"
DOCKER_IMAGE = "de01-image"
DOCKER_TAG = "latest"

docker/build:
	docker build -t $(DOCKER_IMAGE) .
	
docker/push: docker/build
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(AWS_ECR_REPO):$(DOCKER_TAG)
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(AWS_ECR_REPO):$(DOCKER_TAG)
	aws lambda update-function-code --function-name $(AWS_LAMBDA_FUNCTION) --image-uri $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(AWS_ECR_REPO):$(DOCKER_TAG)

docker/run:
	docker run -p 9000:8080 $(DOCKER_IMAGE):$(DOCKER_TAG) app.lambda_handler

docker/test:
	curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'