# Amazon WorkMail Restricted Mailboxes
This application enables you to restrict certain mailboxes from within your Amazon WorkMail organization to send and receive internal emails only. 

Specifically, email messages sent from an external email address to your organization are bounced for restricted mailboxes and are allowed for other mailboxes in your organization. Email messages sent from an restricted mailbox are bounced for external recipients and are allowed for internal recipients. Optionally, this application enables you to receive a copy of such rejected email to a specific mailbox in your organization thereby enabling you to investigate it later.

By default, the code provided here categorizes an email address that uses [default domain](https://docs.aws.amazon.com/workmail/latest/adminguide/default_domain.html) as internal. Email addresses that do not use default domain are categorized as external. You can easily configure emails from additional domains to be categorized as internal by [customizing your Lambda function](https://github.com/aws-samples/amazon-workmail-lambda-templates/tree/master/workmail-restricted-mailboxes-python#customizing-your-lambda-function).

This application identifies a mailbox as restricted if it is member of a specified [WorkMail Group](https://docs.aws.amazon.com/workmail/latest/adminguide/groups_overview.html). As a result, you can control which mailboxes can communicate only internally. 

## Setup
1. Deploy this application via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-restricted-mailboxes-python).
    1. Enter your WorkMail Organization ID. You can find it in the Organization settings tab in the [WorkMail Console](https://console.aws.amazon.com/workmail/) 
    2. Enter the name of the WorkMail Group that has restricted mailboxes as members. To create a new group, follow this [instruction](https://docs.aws.amazon.com/workmail/latest/adminguide/add_new_group.html).
    3. [Optional] Enter the email address of the mailbox where you would like to receive a copy of a rejected email. To create a new dedicated mailbox for this use case, follow this [instruction](https://docs.aws.amazon.com/workmail/latest/adminguide/manage-users.html#add_new_user). 
2. Open the [WorkMail Console](https://console.aws.amazon.com/workmail/) and create a **RunLambda** [Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-rules) that uses this Lambda function.

To further customize your Lambda function, open the [AWS Lambda Console](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions) to edit and test your Lambda function with the built-in code editor.

### Customizing Your Lambda Function
If you would like to categorize emails from additional domains as internal for your organization add these domains to the list [here](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-restricted-mailboxes-python/src/utils.py#L55). 

For more advanced use cases, such as changing your CloudFormation template to create additional AWS resources that will support this application, follow the instructions below.

## Development
Clone this repository from [GitHub](https://github.com/aws-samples/amazon-workmail-lambda-templates).

We recommend creating and activating a virtual environment, for more information see [Creation of virtual environments](https://docs.python.org/3/library/venv.html).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-restricted-mailboxes-python/template.yaml). For more information, see this [documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html).
2. Modify your Lambda function by changing [app.py](https://github.com/aws-samples/amazon-workmail-lambdas-templates/blob/master/workmail-restricted-mailboxes-python/src/app.py).
3. Test your Lambda function locally:
    1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
    2. Configure environment variables at `tst/env_vars.json`.
    3. Configure test event at `tst/event.json`.
    4. Invoke your Lambda function locally using:
    
        `$ sam local invoke WorkMailRestrictedMailboxesFunction -e tst/event.json --env-vars tst/env_vars.json`

Once you have validated that your Lambda function behaves as expected, you are ready to deploy this Lambda function.

### Deployment
If you develop using the AWS Lambda Console, then this section can be skipped.

Please create an S3 bucket if you do not have one yet, see [How do I create an S3 Bucket?](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/create-bucket.html).
and check how to create a [Bucket Policy](https://docs.aws.amazon.com/serverlessrepo/latest/devguide/serverlessrepo-how-to-publish.html#publishing-application-through-cli).
We refer to this bucket as `<Bucket-Name-For-Deployment>`.

This step bundles all your code and configuration to the given S3 bucket. 

```bash
$ sam package \
 --template-file  template.yaml \
 --output-template-file packaged.yaml \
 --s3-bucket <Bucket-Name-For-Deployment>
```

This step updates your Cloud Formation stack to reflect the changes you made, which will in turn update changes made in the Lambda function.
```bash
$ sam deploy \
  --template-file packaged.yaml \
  --stack-name workmail-restricted-mailboxes \
  --parameter-overrides WorkMailOrganizationID=$YOUR_ORGANIZATION_ID RestrictedGroupName=$YOUR_RESTRICTED_GROUP_NAME ReportMailboxAddress=$YOUR_REPORT_MAILBOX\
  --capabilities CAPABILITY_IAM
```
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
