FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.13

COPY requirements.txt  .
RUN pip install -r requirements.txt

# Copy function code
COPY sms_handler.py ${LAMBDA_TASK_ROOT}/
COPY voice_handler.py ${LAMBDA_TASK_ROOT}/
COPY translator.py ${LAMBDA_TASK_ROOT}/

# Default to SMS handler — Terraform’s image_config.command will override for Voice
CMD [ "sms_handler.lambda_handler" ]
