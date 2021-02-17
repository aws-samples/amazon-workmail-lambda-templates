# Amazon WorkMail Chat Bot
This application integrates your email with a basic chat bot using webhooks. Specifically, the application automatically posts to a configured chat channel whenever an email is sent or received which contains a configurable string in the email subject line. The code provided here already supports [Amazon Chime](https://aws.amazon.com/chime/) and [Slack](https://slack.com/), and it can easily be modified to support any other chat application that can be accessed via webhooks.

## Setup
1. Deploy this application via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-chat-bot-python).
    1. Enter the name of your chat client. Supported: Chime, Slack.
    2. Enter the WebHook URL for your chat room. For instructions on how to create a WebHook URL, see the documentation for your chat client: [Amazon Chime](https://docs.aws.amazon.com/chime/latest/ug/webhooks.html), [Slack](https://api.slack.com/incoming-webhooks#create_a_webhook).
    3. [Optional] Configure your chat room to receive messages only from emails that contain certain words in subject. Leave it blank for receiving messages from all emails. 
        For example: Enter **URGENT, Action Required** to receive messages only from emails that contains **URGENT** or **ACTION REQUIRED** in subject.
        Note: Case Insensitive comparison is done. For example: Setting **Urgent** will send messages for emails with subject UrGent, urgent, ...etc.
2. Open the [WorkMail Console](https://console.aws.amazon.com/workmail/) and create a **RunLambda** [Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/create-email-rules.html) that uses this Lambda function.

You now have a working Lambda function that will be triggered by WorkMail based on the rule you created.

If you'd like to add support for a new chat application or further customize your Lambda function, open the [AWS Lambda Console](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions) to edit and test your Lambda function with the built-in code editor. For more information, see [Documentation](https://docs.aws.amazon.com/lambda/latest/dg/code-editor.html).

For more advanced use cases, such as changing your CloudFormation template to create additional AWS resources that will support this application, follow the instructions below.

## Development
Clone this repository from [GitHub](https://github.com/aws-samples/amazon-workmail-lambda-templates).

We recommend creating and activating a virtual environment, for more information see [Creation of virtual environments](https://docs.python.org/3/library/venv.html).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-chat-bot-python/template.yaml). For more information, see this [documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html).
2. Modify your Lambda function by changing [app.py](https://github.com/aws-samples/amazon-workmail-lambdas-templates/blob/master/workmail-chat-bot-python/src/app.py).
3. Test your Lambda function locally:
    1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
    2. Configure environment variables at `tst/env_vars.json`.
    3. Configure test event at `tst/event.json`.
    4. Invoke your Lambda function locally using:
    
        `$ sam local invoke WorkMailChatBotFunction -e tst/event.json --env-vars tst/env_vars.json`


### Deployment
If you develop using the AWS Lambda Console, then this section can be skipped.

Please create an S3 bucket if you do not have one yet, see [How do I create an S3 Bucket?](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/create-bucket.html).
and check how to create a [Bucket Policy](https://docs.aws.amazon.com/serverlessrepo/latest/devguide/serverlessrepo-how-to-publish.html#publishing-application-through-cli).
We refer to this bucket as `<Bucket-Name-For-Deployment>`.

This step bundles all your code and configuration to the given S3 bucket. 

```bash
$ sam package \
 --template-file template.yaml \
 --output-template-file packaged.yaml \
 --s3-bucket <Bucket-Name-For-Deployment>
```

This step updates your Cloud Formation stack to reflect the changes you made, which will in turn update changes made in the Lambda function.
```bash
$ sam deploy \
  --stack-name workmail-chat-bot \
  --template-file packaged.yaml \
  --parameter-overrides ChatClient=$YOUR_CHAT_CLIENT WebhookURL=$YOUR_WEBHOOK_URL ActiveWords=$OPTIONAL_ACTIVE_WORDS \
  --capabilities CAPABILITY_IAM
```

Tip: surround $YOUR_WEBHOOK_URL with quotes.

Your Lambda function is now deployed. You can now configure WorkMail to trigger this function.

## Frequently Asked Questions
### Where are the logs?
You can find the logs in CloudWatch. For more information see [Accessing Amazon CloudWatch logs for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs.html).

### How do I obtain a real message id for my `event.json` file?
1. Make sure your Lambda function prints out the message id from an event.
2. Deploy your Lambda function and add the Lambda rule to your WorkMail organization.
3. Send a test email from your WorkMail account.
4. Check your CloudWatch logs for a printed message id.

Note that you can access messages in transit for a maximum of one day.
