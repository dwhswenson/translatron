# Test checklist for updates to the sms_handler module

## Deployment

- [ ] Login to AWS
- [ ] Build and deploy the container with `./build_and_deploy.sh`
- [ ] Deploy the terraform with `tofu plan` and `tofu apply`

## Testing

- [ ] Use the `test-event.json` file to test the lambda in the AWS console
  * Check whether this works using the CloudWatch logs.
  * If this doesn't work, there's probably a problem with the code.

- [ ] Directly invoke the lambda from the AWS CLI:
  ```bash
  aws lambda invoke \
    --function-name  translatron-sms-handler \
    --payload file://test-event.json \
    --cli-binary-format raw-in-base64-out \
    --log-type Tail  /dev/null \
    | jq -r '.LogResult' | base64 -d
  ```

- [ ] Use the `test-event.json` file to test the lambda's URL locally with:
  ```bash
  curl -X POST $LAMBDA_URL \
   -H "Content-Type: application/json" \
   --data @test-event.json \
   -w "\nHTTP status: %{http_code}\n"
  ```
  * Check whether this works using the CloudWatch logs, as well as the response.
  * If this doesn't work, there's probably a problem with permissions: CORS or something like that

- [ ] Send a test message to the phone number.
