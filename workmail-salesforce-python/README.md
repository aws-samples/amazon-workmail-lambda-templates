# Amazon WorkMail Salesforce Integration

This application replicates your email and calendar communication into Salesforce.

Specifically, the application records your email and calendar communication into a Salesforce Opportunity using a random identifier referred as CaseId. A new CaseId is generated and prefixed in the subject of a new email or calendar item and a new Opportunity is created in Salesforce. All subsequent email or calendar items containing the string "[CaseId:XXX]" in the subject are recorded in the corresponding Opportunity. Additionally, the application also creates Salesforce Contacts and Accounts based on the sender of an incoming email, or recipient of an outgoing email.

This application uses a dedicated Salesforce user for integration that you provide during the setup and uses [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) for persisting your user credentials securely.

This application uses the [simple-salesforce](https://github.com/simple-salesforce/simple-salesforce) REST client to interact with Salesforce. 


## Limitations
1. Recurring meeting requests are not yet handled gracefully.
2. While initiating a new meeting request for an existing CaseId, make sure "[CaseId:XXX]" is present in the subject of the meeting message so that application can record the meeting in the corresponding Opportunity.

## Setup
1. Deploy this application via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-salesforce-python)
    1. Enter the username and password of your Salesforce account.
    2. Enter the security token of your Salesforce account. To create an security token, see [instructions](https://help.salesforce.com/articleView?id=sf.user_security_token.htm&type=5)
2. Configure a synchronous Run Lambda rule for the Lambda function created in step 1, see [instructions](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-rules). Ensure that the value of Rule timeout in your synchronous Run Lambda rule is at least 1 minute. 

It is possible to configure both inbound and outbound email flow rules over the same Lambda function.

You now have a working Lambda function that will be triggered by WorkMail based on the rule you created.

To further customize your Lambda function, open the [AWS Lambda Console](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions) to edit and test your Lambda function with the built-in code editor.

For more information, see [Documentation](https://docs.aws.amazon.com/lambda/latest/dg/code-editor.html).

For more advanced use cases, such as changing your CloudFormation template to create additional AWS resources that will support this application, follow the instructions below.

## Access Control
By default, this serverless application and the resources that it creates can integrate with any [WorkMail Organization](https://docs.aws.amazon.com/workmail/latest/adminguide/organizations_overview.html) in your account, but the application and organization must be in the same region. To restrict that behavior you can either update the SourceArn attribute in [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-salesforce-python/template.yaml)
and then deploy the application by following the steps below **or** update the SourceArn attribute directly in the resource policy of each resource via their AWS Console after the deploying this application, [see example](https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html). 

For more information about the SourceArn attribute, [see this documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-sourcearn).

## Development
Clone this repository from [GitHub](https://github.com/aws-samples/amazon-workmail-lambda-templates).

We recommend creating and activating a virtual environment, for more information see [Creation of virtual environments](https://docs.python.org/3/library/venv.html).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-salesforce-python/template.yaml). See this [documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html) for more details.
2. Modify your Lambda function by changing [app.py](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-salesforce-python/src/app.py).
3. Test your Lambda function locally:
    1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
    2. Configure environment variables at `tst/env_vars.json`.
    3. Configure test event at `tst/event.json`.
    4. Invoke your Lambda function locally using:
    
        `sam local invoke WorkMailSalesforceFunction -e tst/event.json --env-vars tst/env_vars.json`

### Test Message Ids
This application uses a `messageId` passed to the Lambda function to retrieve the message content from WorkMail. When testing, the `tst/event.json` file uses a mock messageId which does not exist. If you want to test with a real messageId, you can configure a WorkMail Email Flow Rule with the Lambda action that uses the Lambda function created in **Setup**, and send some emails that will trigger the email flow rule. The Lambda function will emit the messageId it receives from WorkMail in the CloudWatch logs, which you can
then use in your test event data. For more information see [Accessing Amazon CloudWatch logs for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs.html). Note that you can access messages in transit for a maximum of one day.

Once you have validated that your Lambda function behaves as expected, you are ready to deploy this Lambda function.

### Deployment
If you develop using the AWS Lambda Console, then this section can be skipped.

Please create an S3 bucket if you do not have one yet, see [How do I create an S3 Bucket?](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/create-bucket.html).
and check how to create a [Bucket Policy](https://docs.aws.amazon.com/serverlessrepo/latest/devguide/serverlessrepo-how-to-publish.html#publishing-application-through-cli).
We refer to this bucket as `<Bucket-Name-For-Deployment>`.

This step bundles all your code and configuration to the given S3 bucket. 

```bash
sam package \
 --template-file template.yaml \
 --output-template-file packaged.yaml \
 --s3-bucket <Bucket-Name-For-Deployment>
```

This step updates your Cloud Formation stack to reflect the changes you made, which will in turn update changes made in the Lambda function.
```bash
sam deploy \
 --template-file packaged.yaml \
 --stack-name workmail-salesforce \
 --capabilities CAPABILITY_IAM
```
Your Lambda function is now deployed. You can now configure WorkMail to trigger this function.
