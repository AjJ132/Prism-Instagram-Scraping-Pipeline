aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 717279706981.dkr.ecr.us-east-1.amazonaws.com


@REM # 1. Build the Docker image locally
docker build -t prism-instagram-pipeline-browser-engine .

@REM # 2. Tag the image for AWS ECR (assuming us-east-1 as your region)
docker tag prism-instagram-pipeline-browser-engine:latest 717279706981.dkr.ecr.us-east-1.amazonaws.com/prism-instagram-pipeline-browser-engine:latest

@REM # 3. Push the image to ECR
docker push 717279706981.dkr.ecr.us-east-1.amazonaws.com/prism-instagram-pipeline-browser-engine:latest
