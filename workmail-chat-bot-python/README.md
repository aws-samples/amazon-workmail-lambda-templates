# AWS WorkMail Chat Bot
This application integrates your email with a basic chat bot using webhooks. Specifically, the application automatically posts to a configured chat channel whenever an email is sent or received which contains a configurable string in the email subject line. The code provided here already supports [Amazon Chime](https://aws.amazon.com/chime/) and [Slack](https://slack.com/), and it can easily be modified to support any other chat application that can be accessed via webhooks.

## Setup
1. Deploy this application via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-chat-bot-python).
    1. Enter the name of your chat client. Supported: Chime, Slack.
    2. Enter the WebHook URL for your chat room. For instructions on how to create a WebHook URL, see the documentation for your chat client: [Amazon Chime](https://docs.aws.amazon.com/chime/latest/ug/webhooks.html), [Slack](https://api.slack.com/incoming-webhooks#create_a_webhook).
    3. [Optional] Configure your chat room to receive messages only from emails that contain certain words in subject. Leave it blank for receiving messages from all emails. 
        For example: Enter **URGENT, Action Required** to receive messages only from emails that contains **URGENT** or **ACTION REQUIRED** in subject.
        Note: Case Insensitive comparison is done. For example: Setting **Urgent** will send messages for emails with subject UrGent, urgent, ...etc.
2. Visit [WorkMail Console](https://console.aws.amazon.com/workmail/) and create a **RunLambda** [Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/create-email-rules.html) that uses this Lambda function.

You now have a working Lambda function that will be triggered by WorkMail based on the rule you created.

## Customizing Your Lambda Function
If you'd like to add support for a new chat application or further customize your Lambda function, visit [AWS Lambda Console](https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1#/functions) to edit and test your Lambda function with the built-in code editor. See this [documentation](https://docs.aws.amazon.com/lambda/latest/dg/code-editor.html) for more details.

For more advanced use cases, such as changing your CloudFormation template to create additional AWS resources that will support this application, follow the instructions below.

## Local Development and Testing
Clone this repository from [GitHub](https://github.com/aws-samples/amazon-workmail-lambda-templates).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-chat-bot-python/template.yaml). See this [documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html) for more details.
2. Modify your Lambda function by changing [app.py](https://github.com/sagariiit/amazon-workmail-lambdas-templates/blob/master/workmail-chat-bot-python/src/app.py).
3. Test your Lambda function locally:
    1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
    2. Configure environment variables at `tst/test_env_vars.json`.
    3. Configure test event at `tst/event.json`.
    4. Invoke your Lambda function locally using:
        `sam local invoke WorkMailChatBotFunction -e tst/event.json --env-vars tst/test_env_vars.json`

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
  --stack-name $YOUR_STACK_NAME \
  --parameter-overrides ChatClient=$YOUR_CHAT_CLIENT WebhookURL=$YOUR_WEBHOOK_URL ActiveWords=$OPTIONAL_ACTIVE_WORDS \
  --capabilities CAPABILITY_IAM
```
Your Lambda function is now deployed. You can now configure WorkMail to trigger this function.

### Configure WorkMail
To use this Lambda with WorkMail, follow the instructions at [WorkMail Console](https://console.aws.amazon.com/workmail/) to create a **RunLambda** [Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/create-email-rules.html). These steps will require the full ARN of your Lambda function, which can be retrieved by running the following:

```bash
aws cloudformation describe-stacks \
  --stack-name $YOUR_STACK_NAME \
  --query 'Stacks[].Outputs[0].OutputValue'
```

