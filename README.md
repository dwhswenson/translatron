# Translatron

Translatron is a set of tools to handle translation of Twilio messages and
voice mails using serverless AWS infrastructure. It allows you to use different
translation services.

Overall, Translatron consists of three main components:

1. A Python library to simplify writing the Twilio-and-translation focused AWS lambda
   functions.
2. Terraform modules to deploy the necessary AWS infrastructure.
3. A set of example lambda functions that use the Python library to perform
   translation of Twilio messages and voice mails.
