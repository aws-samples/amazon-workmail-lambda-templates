# Amazon WorkMail Message Flow State Machine

This application enables you to use AWS Step Functions to orchestrate multiple AWS Lambda functions for Amazon WorkMail and implement additional business logic into your WorkMail message flow.

## Setup
1. Deploy this application via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-message-flow-state-machine).
    1. [Optional] Enter `MachineStateForOutput` to specify state of the Step Function whose output should be returned back to WorkMail. By default, output of the succeeded execution event is used.
    2. [Optional] Enter `WaitTimeForExecution` to specify number of seconds to wait for result after the state machine is first invoked, useful when step function finishes within few seconds. By default, value is 1 second.
2. Open the [WorkMail Console](https://console.aws.amazon.com/workmail/) and create a synchronous **RunLambda** [Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-rules) that uses this Lambda function.
    1. `Rule timeout` must be more than the maximum duration of the step function execution. See [this section](#How timeouts and retry logic are part of this solution) for more details.
3. Open the [AWS Step Functions Console](https://console.aws.amazon.com/states/) and modify the new state machine with your business logic. 

To further customize your Lambda function, open the [AWS Lambda Console](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions) to edit and test your Lambda function with the built-in code editor.

`MachineStateForOutput` allows you to build more asynchronous capabilities into your state machine without delaying message delivery.

Use `WaitTimeForExecution` only if your state machine is known to always execute within few seconds so that the benefit of waiting is worth more than the delay caused due to retury logic.

## How timeouts and retry logic are part of this solution

If the Step Function state machine does not finish execution before `WaitTimeForExecution` or the `MachineStateForOutput` result is not available by that time, then the state machine's executionArn is saved to a Dynamo DB table with a TTL of 240 minutes (maximum value of `Rule timeout`) and the Lambda function will return an error signaling to WorkMail to retry again later. 

WorkMail will keep re-invoking the function until it gets a result or `Rule timeout` is reached. Upon each subsequent invocation lambda function will look up the executionArn of the state machine from the Dynamo DB table and check for result. If no result is returned back to WorkMail before 240 minutes then the rule's default action will take effect.

Depending on your use case, you may choose to raise the value of `WaitTimeForExecution` if you know the state machine will return in a predictable amount of time of in order of seconds since long running Lambda functions incur costs.

## Modifying your Step Functions state machine

Once you have finished the setup, send a test email message in to your WorkMail mailbox. From the Step Functions console you will see a successful execution. 
In the execution, expand ExecutionSucceeded to see the output from the state machine's execution; this output was used by the Lambda function to return to the WorkMail Message Flow API.

You can configure the state machine to return different output based on the logic you want to define. Since the input to the state machine is the same as the input that was sent to the WorkMail Message Flow Lambda, you can pass this input into additional states within your state machine that execute other WorkMail functions; which you can subsequently use the results from other functions to return back via the execution output.

Finally, as described above, you can set the `MachineStateForOutput` to make lambda function look for the output from a specific state of your state machine. This allows your state machine to quickly delivery a final result back to the asynchronous message flow while allowing your state machine to execute additional states without delaying message delivery.

### Customizing Your Lambda Function

For more advanced use cases, such as changing your CloudFormation template to create additional AWS resources that will support this application, follow the instructions below.

## Development
Clone this repository from [GitHub](https://github.com/aws-samples/amazon-workmail-lambda-templates).

We recommend creating and activating a virtual environment, for more information see [Creation of virtual environments](https://docs.python.org/3/library/venv.html).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-message-flow-state-machine/template.yaml). For more information, see this [documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html).
2. Modify your Lambda function by changing [app.py](https://github.com/aws-samples/amazon-workmail-lambdas-templates/blob/master/workmail-message-flow-state-machine/src/app.py).
3. Test your Lambda function locally:
    1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
    2. Configure environment variables at `tst/env_vars.json`.
    3. Configure test event at `tst/event.json`.
    4. Invoke your Lambda function locally using:
    
        `sam local invoke MfsmFunction -e tst/event.json --env-vars tst/env_vars.json`

### Test Message Ids
This application uses a `messageId` passed to the Lambda function to retrieve the message content from WorkMail. When testing, the `tst/event.json` file uses a mock messageId which does not exist. If you want to test with a real messageId, you can configure a WorkMail Email Flow Rule with the Lambda action that uses the Lambda function created in **Setup**, and send some emails that will trigger the email flow rule. The Lambda function will emit the messageId it receives from WorkMail in the CloudWatch logs, which you can
then use in your test event data. For more information see [Accessing Amazon CloudWatch logs for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs.html). Note that you can access messages in transit for a maximum of one day.

Once you have validated that your Lambda function behaves as expected, you are ready to deploy this Lambda function.

## Access Control
By default, this serverless application and the resources that it creates can integrate with any [WorkMail Organization](https://docs.aws.amazon.com/workmail/latest/adminguide/organizations_overview.html) in your account, but the application and organization must be in the same region. To restrict that behavior you can either update the SourceArn attribute in [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-message-flow-state-machine/template.yaml)
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
 --template-file template.yaml \
 --output-template-file packaged.yaml \
 --s3-bucket <Bucket-Name-For-Deployment>
```

This step updates your CloudFormation stack to reflect the changes you made, which will in turn update changes made in the Lambda function.
```bash
sam deploy \
  --template-file packaged.yaml \
  --stack-name myMailFlowMachine \
  --capabilities CAPABILITY_IAM
```
Your Lambda function and Step Functions state machine are now deployed. You can now configure WorkMail to trigger this function and modify the state machine to implement your business logic.
