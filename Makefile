AWS_ACCOUNT_ID ?=
AWS_REGION ?=
AWS_ECR_REPO = "de01-lambda-repo"
AWS_LAMBDA_FUNCTION = "de01_lambda"
DOCKER_IMAGE = "de01-image"
DOCKER_TAG = "latest"

docker/build:
	docker build -t $(DOCKER_IMAGE) ./lambda
	
docker/push: docker/build
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(AWS_ECR_REPO):$(DOCKER_TAG)
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(AWS_ECR_REPO):$(DOCKER_TAG)
	aws lambda update-function-code --function-name $(AWS_LAMBDA_FUNCTION) --image-uri $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(AWS_ECR_REPO):$(DOCKER_TAG)

docker/run:
	docker run -p 9000:8080 $(DOCKER_IMAGE):$(DOCKER_TAG) app.lambda_handler

docker/test:
	curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"Records": [{"eventVersion": "2.1", "eventSource": "aws:s3", "awsRegion": "eu-central-1", "eventTime": "2024-05-08T10:09:45.937Z", "eventName": "ObjectCreated:Put", "userIdentity": {"principalId": "AWS:AIDA4XFRBMUAIR3CT4Z6R"}, "requestParameters": {"sourceIPAddress": "83.10.14.198"}, "responseElements": {"x-amz-request-id": "KC6Q4PQAYE0GMQA1", "x-amz-id-2": "8rvLj1I4US49N2HfNkqmDNXE7nK/KSUpP3Cz0CEWGigLVQOLg0+kFTXp10jqbZTYfN0XFlfJpXZhofnaVftvLtkIQaX3NJiJ"}, "s3": {"s3SchemaVersion": "1.0", "configurationId":"a99d1f9e-4361-4fdd-8ec7-25d6553e13c8","bucket":{"name":"de01-source-files","ownerIdentity":{"principalId":"A25EHJ0XK9Z875"},"arn":"arn:aws:s3:::de01-source-files"},"object":{"key":"data_2024_02_26.json","size":479,"eTag":"7ef8c2513584a5cdde9a21647105354a","sequencer":"00663B4F69DA003BDF"}}}]}'