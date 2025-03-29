docker build --platform linux/amd64 -t khatoon-customer-lambda .
docker tag khatoon-customer-lambda:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/khatoon-customer-lambda:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/khatoon-customer-lambda:latest
