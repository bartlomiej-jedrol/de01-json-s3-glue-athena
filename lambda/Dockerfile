# Specify base image
FROM public.ecr.aws/lambda/python:3.10

# Set working directory to environment variable provided by AWS Lambda
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy Python requirements file
COPY requirements.txt .

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY . . 

# Specify the handler of the Lambda function - entry point for the container
CMD [ "app.lambda_handler" ]