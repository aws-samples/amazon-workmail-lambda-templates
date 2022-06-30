# Amazon WorkMail / Exchange based Custom Availability Provider

This application shows how to get user availability from a non-public EWS endpoint.

The high level overview:
- A user makes an EWS `GetUserAvailability` request to WorkMail for mailboxes that
  are not hosted in the WorkMail organization.
- WorkMail invokes the Custom Availability Provider lambda function.
- The lambda function obtains credentials for the remote EWS endpoint from secrets
  manager.
- The lambda function calls `GetUserAvailability` on the remote EWS endpoint and
  relays the result back to WorkMail.

## Setup

1. Set the correct values in the `exchange_secrets.json` file.

   1. `ews_url` - the URL to the remote EWS endpoint
   2. `ews_username` - the username of the user used to access the remote EWS endpoint
   3. `ews_password` - the password of the user used to access the remove EWS endpoint

2. Upload `exchange_secrets.json` to AWS Secrets Manager:
   ```shell
   aws secretsmanager create-secret --name production/ExchangeSecrets --secret-string file://exchange_secrets.json
   ```

3. Deploy this application via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-cap-exchange):

   1. Keep the default `production/ExchangeSecrets` value
   2. Enter your WorkMail organization id

4. Create an AvailabilityConfiguration for the new lambda function
   ```shell
   aws workmail create-availability-configuration \
   --organization-id <YOUR_ORGANIZATION_ID> \
   --domain-name <EXTERNAL_DOMAIN_NAME> \
   --lambda-provider 'LambdaArn=<ARN_FROM_STEP_3>'
   ```

You now have a working Lambda function that will handle user availabilty requests.

If you'd like to customize your Lambda function, open the [AWS Lambda Console](https://console.aws.amazon.com/lambda) to edit and test your Lambda 
function with the built-in code editor. For more information, see [Documentation](https://docs.aws.amazon.com/lambda/latest/dg/code-editor.html).

For more advanced use cases, such as changing your CloudFormation template to create additional AWS resources that will support this application, follow the instructions below.

## Development

Clone this repository from [Github](https://raw.githubusercontent.com/aws-samples/amazon-workmail-lambda-templates/master/workmail-cap-exchange).

We recommend creating and activating a virtual environment, for more information see [Creation of virtual environments](https://docs.python.org/3/library/venv.html).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-cap-exchange/template.yaml). For 
   more information, see [documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html).

2. Modify your Lambda function by changing [app.py](https://github.com/aws-samples/amazon-workmail-lambdas-templates/blob/master/workmail-cap-exchange/src/app.py).

3. Test your lambda function locally:
   
    1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
   
    2. Put values to `exchange_secrets.json` and create/update a secret to AWS Secrets Manager:
        ```shell 
        aws secretsmanager create-secret --name production/ExchangeSecrets --secret-string file://exchange_secrets.json
        aws secretsmanager update-secret --secret-id production/ExchangeSecrets --secret-string file://exchange_secrets.json 
       ```

    3. Fill out files in `tst` folder with your corresponding values

### Testing

Testing Lambda locally:
```shell
sam local invoke WorkMailCapExchangeFunction -e tst/lambda_query_availability.json --env-vars tst/env_vars.json
```

### Deployment

```shell
sam deploy --guided
```

Your Lambda function is now deployed. The output will contain `WorkMailCapExchangeFunctionName` which you can use
to invoke the function using `awscli`:
```shell
aws lambda invoke --function-name <function name from previous step> --payload 'file://tst/lambda_query_availability.json' /dev/stderr >/dev/null
```

## Troubleshooting 

### Where can I find logs?

The logs can be found in CloudWatch. To get more detailed logging, change the loglevel in 
[app.py](https://github.com/aws-samples/amazon-workmail-lambdas-templates/blob/master/workmail-cap-exchange/src/app.py) 
to `DEBUG`.
