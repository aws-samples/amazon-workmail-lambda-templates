# Amazon WorkMail Upstream Gateway Filter

This application enables you to filter messages to Junk E-Mail for multiple recipients based on the value of an email header added by an upstream email security gateway.

Define the FILTER_HEADER_NAME and FILTER_HEADER_REGEX evironment variables to control which messages are filtered. If the value of the header matches the regular expression then the message will be filtered into the mailbox's Junk E-Mail folder.

## Setup
1. Deploy this application via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-upstream-gateway-filter).
    1. Enter the name of the email header that which the upstream email security gateway adds to incoming messages. 
    2. Enter the regular expression to match against the value of the header.
2. Open the [WorkMail Console](https://console.aws.amazon.com/workmail/) and create a **RunLambda** [Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-rules) that uses this Lambda function.

To further customize your Lambda function, open the [AWS Lambda Console](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions) to edit and test your Lambda function with the built-in code editor.

### Customizing Your Lambda Function

For more advanced use cases, such as changing your CloudFormation template to create additional AWS resources that will support this application, follow the instructions below.

## Development
Clone this repository from [GitHub](https://github.com/aws-samples/amazon-workmail-lambda-templates).

We recommend creating and activating a virtual environment, for more information see [Creation of virtual environments](https://docs.python.org/3/library/venv.html).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-upstream-gateway-filter/template.yaml). For more information, see this [documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html).
2. Modify your Lambda function by changing [app.py](https://github.com/aws-samples/amazon-workmail-lambdas-templates/blob/master/workmail-upstream-gateway-filter/src/app.py).
3. Test your Lambda function locally:
    1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
    2. Configure environment variables at `tst/env_vars.json`.
    3. Configure test event at `tst/event.json`.
    4. Invoke your Lambda function locally using:
    
        `sam local invoke WorkMailUpstreamGatewayFilterFunction -e tst/event.json --env-vars tst/env_vars.json`

### Test Message Ids
This application uses a `messageId` passed to the Lambda function to retrieve the message content from WorkMail. When testing, the `tst/event.json` file uses a mock messageId which does not exist. If you want to test with a real messageId, you can configure a WorkMail Email Flow Rule with the Lambda action that uses the Lambda function created in **Setup**, and send some emails that will trigger the email flow rule. The Lambda function will emit the messageId it receives from WorkMail in the CloudWatch logs, which you can
then use in your test event data. For more information see [Accessing Amazon CloudWatch logs for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs.html). Note that you can access messages in transit for a maximum of one day.

Once you have validated that your Lambda function behaves as expected, you are ready to deploy this Lambda function.

## Access Control
By default, this serverless application and the resources that it creates can integrate with any [WorkMail Organization](https://docs.aws.amazon.com/workmail/latest/adminguide/organizations_overview.html) in your account, but the application and organization must be in the same region. To restrict that behavior you can either update the SourceArn attribute in [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-upstream-gateway-filter/template.yaml)
and then deploy the application by following the steps below **or** update the SourceArn attribute directly in the resource policy of each resource via their AWS Console after the deploying this application, [see example](https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html). 

For more information about the SourceArn attribute, [see this documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-sourcearn).

### Deployment
If you develop using the AWS Lambda Console, then this section can be skipped.

Please create an S3 bucket if you do not have one yet, see [How do I create an S3 Bucket?](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/create-bucket.html).
and check how to create a [Bucket Policy](https://docs.aws.amazon.com/serverlessrepo/latest/devguide/serverlessrepo-how-to-publish.html#publishing-application-through-cli).
We refer to this bucket as `<Bucket-Name-For-Deployment>`.

This step bundles all your code and configuration to the given S3 bucket. 

```bash
sam package \
 --template-file  template.yaml \
 --output-template-file packaged.yaml \
 --s3-bucket <Bucket-Name-For-Deployment>
```

This step updates your Cloud Formation stack to reflect the changes you made, which will in turn update changes made in the Lambda function.
```bash
sam deploy \
  --template-file packaged.yaml \
  --stack-name workmail-upstream-gateway-filter \
  --parameter-overrides FilterHeaderName=$YOUR_FILTER_HEADER_NAME FilterHeaderRegex=$YOUR_FILTER_HEADER_REGEX\
  --capabilities CAPABILITY_IAM
```
Your Lambda function is now deployed. You can now configure WorkMail to trigger this function.
