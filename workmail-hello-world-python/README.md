# AWS WorkMail Hello World

This is a hello world example of the WorkMail Lambda feature. For more information see [AWS WorkMail Lambda documentation](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html)

To use this application you can deploy it via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-hello-world-python)

### Local development

First, [set up the SAM CLI](https://aws.amazon.com/serverless/sam/).

Now, test the application locally using:

`sam local invoke WorkMailHelloWorldFunction -e event.json`

### Deploying

```bash
sam package \
 --template-file template.yaml \
 --output-template-file packaged.yaml \
 --s3-bucket $YOUR_BUCKET_NAME
```

```bash
sam deploy \
 --template-file packaged.yaml \
 --stack-name workmail-hello-world \
 --capabilities CAPABILITY_IAM
```

### Configure WorkMail
Find the ARN of your new Lambda function using:

```bash
aws cloudformation describe-stacks \
  --stack-name workmail-hello-world \
  --query 'Stacks[].Outputs[0].OutputValue'
```

Now you can go to WorkMail console and configure an outbound rule to use your new Lambda.

