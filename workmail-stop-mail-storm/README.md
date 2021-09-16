# Email Storm protection application for Amazon WorkMail

An [email storm](https://en.wikipedia.org/wiki/Email_storm) is a sudden spike of messages on an email distribution list. This can cause hundreds of messages to flood user mailboxes.
 
This application helps you protect [Amazon WorkMail Groups](https://docs.aws.amazon.com/workmail/latest/adminguide/groups_overview.html) within your organization from email storms. It is built on top of the [Run Lambda Email Flow Rules](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-rules) for Amazon WorkMail.

### Setup

1. Deploy the application from the [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-stop-mail-storm). Provide the following items:
    1. The email addresses that you want to protect from email storms
    1. The threshold of emails per minute
1. Open the [Amazon WorkMail Console](https://console.aws.amazon.com/workmail/) and create a [RunLambda Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-rules) that uses the AWS Lambda function you created in step 1.

You now have a working Lambda function that is triggered by Amazon WorkMail based on the rule you created.

### How does it work?

For each protected Amazon WorkMail group, the application creates an [Amazon CloudWatch metric](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html) that counts the number of emails received per minute. The application also creates an [Amazon CloudWatch alarm](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html) with a user-configured threshold on that metric.

When an email is received by a protected group, the application publishes a data point for the metric created for the group and verifies the alarm state. If the alarm is in ALARM state then the email is bounced before it is distributed.

### Customizing your Lambda function
You can customize your Lambda function by editing and testing it in the [AWS Lambda Console](https://console.aws.amazon.com/lambda/home) built-in code editor. For more information on the code editor, see [here](https://docs.aws.amazon.com/lambda/latest/dg/code-editor.html).

You can modify the alarm conditions [here](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-stop-mail-storm/src/app.py#L51). For more information, see [CloudWatch alarms documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricAlarm.html).

For more advanced use cases, such as changing your AWS CloudFormation template to create additional AWS resources that will support this application, see [Local development](#local-development)

### Costs, performance and availability considerations
This application emits a metric and queries the alarm state for each email received by a protected email address. Each of these actions can incur [extra costs](https://aws.amazon.com/cloudwatch/pricing/).

Each CloudWatch action also adds a delay, usually less than one second. The actions can fail if the CloudWatch or Lambda service fails. Potential delays and failures are mitigated by timeouts and retry limits configured in Amazon WorkMail and your Lambda function. For more information, see [Configuring AWS Lambda for Amazon WorkMail](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-rules) in the Amazon WorkMail Administration Guide.

The DescribeAlarms API used to verify CloudWatch alarms is limited to nine requests per second. If you need a higher threshold, you can [request a quota increase](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_limits.html).

### Access Control
By default, this serverless application and the resources that it creates can integrate with any [WorkMail Organization](https://docs.aws.amazon.com/workmail/latest/adminguide/organizations_overview.html) in your account, but the application and organization must be in the same region. To restrict that behavior you can either update the SourceArn attribute in [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-stop-mail-storm/template.yaml)
and then deploy the application by following the steps below **or** update the SourceArn attribute directly in the resource policy of each resource via their AWS Console after the deploying this application, [see example](https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html). 

For more information about the SourceArn attribute, [see this documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-sourcearn).

## Local development
Cloning this repository from [GitHub](https://github.com/aws-samples/amazon-workmail-lambda-templates).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/workmail-stop-mail-storm/blob/master/workmail-stop-mail-storm/template.yaml). For more information, see [Template Reference in the AWS CloudFormation User Guide](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html).
2. Modify your Lambda function by changing [app.py](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-stop-mail-storm/src/app.py).
3. Test your Lambda function locally by completing the following tasks:
    1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
    2. Configure a test event at `event.json`.
    3. Invoke your Lambda function locally using:
        `sam local invoke -e tst/event.json -n tst/environment_variables.json`

### Test Message Ids
This application uses a `messageId` passed to the Lambda function to retrieve the message content from WorkMail. When testing, the `tst/event.json` file uses a mock messageId which does not exist. If you want to test with a real messageId, you can configure a WorkMail Email Flow Rule with the Lambda action that uses the Lambda function created in **Setup**, and send some emails that will trigger the email flow rule. The Lambda function will emit the messageId it receives from WorkMail in the CloudWatch logs, which you can
then use in your test event data. For more information see [Accessing Amazon CloudWatch logs for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs.html). Note that you can access messages in transit for a maximum of one day.

Once you have validated that your Lambda function behaves as expected, you are ready to deploy this Lambda function.

### Deploying a local version
This step bundles all your code and configuration to your S3 bucket.

```bash
sam package \
 --template-file template.yaml \
 --output-template-file packaged.yaml \
 --s3-bucket $YOUR_BUCKET_NAME
```

This step updates your CloudFormation stack to reflect the changes you made, which will in turn updates the changes made in your Lambda function.
```bash
sam deploy \
 --template-file packaged.yaml \
 --stack-name workmail-stop-mail-storm \
 --capabilities CAPABILITY_IAM
```
Your Lambda function is now deployed. You can now configure Amazon WorkMail to trigger this function on inbound email.

### Configure Amazon WorkMail
To use this Lambda with Amazon WorkMail, use the [Amazon WorkMail Console](https://console.aws.amazon.com/workmail/) to create a **RunLambda** [email flow rule](https://docs.aws.amazon.com/workmail/latest/adminguide/create-email-rules.html). [Configuring AWS Lambda for Amazon WorkMail](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-rules) in the Amazon WorkMail Administration Guide. 

These steps will require the full ARN of your Lambda function. Get the ARN by running the following command:

```bash
aws cloudformation describe-stacks \
  --stack-name workmail-stop-mail-storm \
  --query 'Stacks[].Outputs[0].OutputValue'
```
