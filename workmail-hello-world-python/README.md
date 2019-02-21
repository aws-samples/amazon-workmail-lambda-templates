# Amazon WorkMail Hello World

This is a hello world example of the WorkMail Lambda feature. For more information see [AWS WorkMail Lambda documentation](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html)

To use this application you can deploy it via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-hello-world-python)

### Local development
Clone this repository from [GitHub](https://github.com/aws-samples/amazon-workmail-lambda-templates).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-hello-world-python/template.yaml). See this [documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html) for more details.
2. Modify your Lambda function by changing [app.py](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-hello-world-python/workmail-hello-world/app.py).
3. Test your Lambda function locally:
    1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
    2. Configure test event at `event.json`.
    3. Invoke your Lambda function locally using:
        `sam local invoke WorkMailHelloWorldFunction -e event.json`

Once you have validated that your Lambda function behaves as expected, you are ready to deploy this Lambda function.

### Deploying
This step bundles all your code and configuration to the given S3 bucket.

```bash
sam package \
 --template-file template.yaml \
 --output-template-file packaged.yaml \
 --s3-bucket $YOUR_BUCKET_NAME
```

This step updates your Cloud Formation stack to reflect the changes you made, which will in turn update changes made in the Lambda function.
```bash
sam deploy \
 --template-file packaged.yaml \
 --stack-name workmail-hello-world \
 --capabilities CAPABILITY_IAM
```
Your Lambda function is now deployed. You can now configure WorkMail to trigger this function.

### Configure WorkMail
To use this Lambda with WorkMail, follow the instructions at [WorkMail Console](https://console.aws.amazon.com/workmail/) to create a **RunLambda** [Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/create-email-rules.html). These steps will require the full ARN of your Lambda function, which can be retrieved by running the following:

```bash
aws cloudformation describe-stacks \
  --stack-name workmail-hello-world \
  --query 'Stacks[].Outputs[0].OutputValue'
```

