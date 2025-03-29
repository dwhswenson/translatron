# Test checklist for updates to the sms_handler module

## Deployment

- [ ] Login to AWS (e.g., `aws sso login`) and then login to ECR:

  ```bash
  aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com
  ```

- [ ] Build and deploy the container with `bash build_and_deploy.sh`
- [ ] Update the dev version in terraform (`variables.tf`)
- [ ] Deploy the terraform with `tofu plan` and `tofu apply`

## Testing

- [ ] Use the `test-event.json` file to test the lambda in the AWS console
  * Check whether this works using the CloudWatch logs.
  * If this doesn't work, there's probably a problem with the code.
- [ ] Use the `test-event.json` file to test the lambda's URL locally with:
  ```bash
  curl -X POST -d @test-event.json 
  ```
  * Check whether this works using the CloudWatch logs, as well as the response.
  * If this doesn't work, there's probably a problem with permissions: CORS or something like that
- [ ] Send a test message to the phone number.
