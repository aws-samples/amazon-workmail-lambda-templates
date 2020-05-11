# Amazon WorkMail Restricted Mailboxes
This application enables you to restrict certain mailboxes from within your Amazon WorkMail organization to send and receive internal emails only. 

Specifically, email messages sent from an external email address to your organization are bounced for restricted mailboxes and are allowed for other mailboxes in your organization. Email messages sent from an restricted mailbox are bounced for external recipients and are allowed for internal recipients. Optionally, this application enables you to receive a copy of such rejected email to a specific mailbox in your organization thereby enabling you to investigate it later.

By default, the code provided here categorizes an email address that uses [default domain](https://docs.aws.amazon.com/workmail/latest/adminguide/default_domain.html) as internal. Email addresses that do not use default domain are categorized as external. You can easily configure emails from additional domains to be categorized as internal by [customizing your lambda function](https://github.com/aws-samples/amazon-workmail-lambda-templates/tree/master/workmail-restricted-mailboxes-python#customizing-your-lambda-function)

This application identifies a mailbox as restricted if it is member of a specified [WorkMail Group](https://docs.aws.amazon.com/workmail/latest/adminguide/groups_overview.html). As a result, you can control which mailboxes can communicate only internally. 

## Setup
1. Deploy this application via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-restricted-mailboxes-python).
    1. Enter your WorkMail Organization ID. You can find it in the Organization settings tab in the [WorkMail Console](https://console.aws.amazon.com/workmail/) 
    2. Enter the name of the WorkMail Group that has restricted mailboxes as members. To create a new group, follow this [instruction](https://docs.aws.amazon.com/workmail/latest/adminguide/add_new_group.html).
    3. [Optional] Enter the email address of the mailbox where you would like to receive a copy of a rejected email. To create a new dedicated mailbox for this use case, follow this [instruction](https://docs.aws.amazon.com/workmail/latest/adminguide/manage-users.html#add_new_user). 
2. Open the [WorkMail Console](https://console.aws.amazon.com/workmail/) and create a **RunLambda** [Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-rules) that uses this Lambda function.

You now have a working Lambda function that will be triggered by WorkMail based on the rule you created.

## Customizing Your Lambda Function
To further customize your Lambda function, open the [AWS Lambda Console](https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1#/functions) to edit and test your Lambda function with the built-in code editor.

If you would like to categorize emails from additional domains as internal for your organization add these domains to the list [here](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-restricted-mailboxes-python/src/utils.py#L55). 

For more information, see this [documentation](https://docs.aws.amazon.com/lambda/latest/dg/code-editor.html).

For more advanced use cases, such as changing your CloudFormation template to create additional AWS resources that will support this application, follow the instructions below.

## Local Development and Testing
Clone this repository from [GitHub](https://github.com/aws-samples/amazon-workmail-lambda-templates).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-restricted-mailboxes-python/template.yaml). For more information, see this [documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html).
2. Modify your Lambda function by changing [app.py](https://github.com/aws-samples/amazon-workmail-lambdas-templates/blob/master/workmail-restricted-mailboxes-python/src/app.py).
3. Test your Lambda function locally:
    1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
    2. Configure environment variables at `tst/test_env_vars.json`.
    3. Configure test event at `tst/event.json`.
    4. Invoke your Lambda function locally using:
        `sam local invoke WorkMailRestrictedMailboxesFunction -e tst/event.json --env-vars tst/test_env_vars.json`

### Test Message Ids
This application uses a `messageId` passed to the Lambda function to retrieve the message content from WorkMail and post it to your blog. When testing, the `tst/event.json` file uses a mock messageId which does not exist. If you want to test with a real messageId, you can configure a WorkMail Email Flow Rule with the Lambda action using this Lambda, and send some emails to trigger it. The Lambda function will emit the messageId it receives from WorkMail in the logs, which you can then use in your test event data.

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
  --parameter-overrides WorkMailOrganizationID=$YOUR_ORGANIZATION_ID RestrictedGroupName=$YOUR_RESTRICTED_GROUP_NAME ReportMailboxAddress=$YOUR_REPORT_MAILBOX\
  --capabilities CAPABILITY_IAM
```
Your Lambda function is now deployed. You can now configure WorkMail to trigger this function.

### Configure WorkMail
To use this Lambda with WorkMail, follow the instructions at [WorkMail Console](https://console.aws.amazon.com/workmail/) to create a **RunLambda** [Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-rules). These steps will require the full ARN of your Lambda function, which can be retrieved by running the following:

```bash
aws cloudformation describe-stacks \
  --stack-name $YOUR_STACK_NAME \
  --query 'Stacks[].Outputs[0].OutputValue'
```

