FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.13

# NOTE: this Dockerfile requires us to build it from the parent directory.
# All of that is handled in ./build-and-push.sh, but if we no longer need to
# copy from local source (can pip install), that can be removed.

COPY lambdas/requirements.txt  .
RUN pip install -r requirements.txt

COPY src/translatron/ ${LAMBDA_TASK_ROOT}/translatron/

# Copy function code
COPY lambdas/sms_handler.py ${LAMBDA_TASK_ROOT}/
COPY lambdas/sms_handler_2.py ${LAMBDA_TASK_ROOT}/
COPY lambdas/voice_handler.py ${LAMBDA_TASK_ROOT}/
COPY lambdas/translator.py ${LAMBDA_TASK_ROOT}/

# Default to SMS handler — Terraform’s image_config.command will override for Voice
CMD [ "sms_handler.lambda_handler" ]
