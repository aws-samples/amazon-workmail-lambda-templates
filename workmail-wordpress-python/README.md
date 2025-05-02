# Amazon WorkMail WordPress Blog Poster
This application integrates your email with a WordPress blog, allowing you to automatically create blog drafts from emails sent or received.

When the application is triggered, it will check for a certain trigger phrase in the email subject. If the phrase is present, it will create a blog post on your site in *draft* state, with the following properties:
* Title: `email_subject`
* Contents: `email_body`, prepended with `Author: email_sender`

After you have cloned this application you can customize this behavior.

## Setup

### 1. Create Your WordPress Application
First, create a WordPress application. This will allow access to the WordPress API.

1. Go to https://developer.wordpress.com/apps/new/
2. Choose a name and a description for your application.
  1. Add a link to some documentation page, such as the docs associated with this SAR app.
3. For the redirect URL, enter  `http://localhost`.
4. For the Javascript Origins, enter `http://localhost`. 
  1. This is only needed if you want to make unauthenticated API calls, which is not part of this procedure.
5. Answer the security question.
6. For Application Type, select Web.
7. Choose **Create**.

You are redirected to a new page containing your application details. Copy and save the Client ID and Client Secret in a safe place. You will use these later

### 2. Set Up Blog Poster User
Next, set up a dedicated WordPress user with permissions to post to your blog. In a later step, you will create a Lambda function that will inherit the user’s permissions and act on behalf of the user. The best practice is to restrict the user to only the permissions that it needs.

If you have an existing WordPress user that meets these requirements, skip to Step 3, Get OAuth Access Token.

**To set up a new user:**
1. Sign in to wordpress.com and choose your blog from the navigation bar at the top of the page.
2. Choose **Manage** > **People** > **Invite**.
3. Enter the email address of the new user.
4. Choose a Role. We recommend Author, which allows the user to add posts but does not allow them access to site administration functionality.
5. Check the email of the new user, and accept the invitation from WordPress. If the user does not yet have an account, they can create one from the link in the email.

### 3. Get OAuth Access Token
Now that you have a user that can publish posts, you need an access token for that user. The access token will be used by your Lambda. 

1. Go to https://github.com/Automattic/node-wpcom-oauth to get the WordPress-supported example auth code.
2. Clone the git repo, and follow the instructions in example/Readme.md to get started.
3. In your web browser, navigate to `http://localhost:3001` and follow the directions to get the API token. **Note:** When accepting the WordPress application's request to access your blog, make sure to sign in as the Blog Poster User created in Step 2, Set Up Blog Poster User.
4. After authenticating to WordPress, you are redirected back to a localhost URL. Choose the **Let's get it** button. You should see the message **Request has been successful**.
5. Copy and save the access token in a safe place. It should look like this:
   `abEXAMPLE186bFX@!x1VL#1dxgi8C(M&oXP365)%cMmQ!#l5I%uYt)%KjLyNc90Q`

For more information, see the [WordPress OAuth2 Documentation](https://developer.wordpress.com/docs/oauth2/).

### 4. Store Access Token in AWS Secrets Manager
Next, store the above access token in AWS Secrets Manager so that your Lambda can access it. The AWS Serverless Application Repository does not yet support automatic creation of Secrets Manager resources, so you must do this manually.

The following examples show how to store the access token in AWS Secrets Manager using the AWS CLI. For more information, see AWS Secrets Manager documentation (https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_create-basic-secret.html).

1. From your terminal, run the following command to upload the token:

```bash
aws secretsmanager --region REGION create-secret --name 'SECRET_NAME' --secret-string 'ACCESS_TOKEN'
```

Variable descriptions:
* REGION: The region you are working in (e.g. 'us-east-1')
* SECRET_NAME: The name of the secret to create. You will later use this when creating your CloudFormation template.
* ACCESS_TOKEN: The access token created above


### 5. Deploy Application
1. Deploy this application via [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:489970191081:applications~workmail-wordpress-python).
 1. Enter the domain name of your blog, without any leading or trailing text, e.g. 'myblog.home.blog'.
 2. Enter the name of the AWS Secrets Manager secret created in step 4.
 3. Choose **Deploy**
2. Open the [WorkMail Console](https://console.aws.amazon.com/workmail/) and create a **RunLambda** [Inbound Email Flow Rule](https://docs.aws.amazon.com/workmail/latest/adminguide/create-email-rules.html) that uses this Lambda function.

The Lambda function will be triggered by Amazon WorkMail based on the rule you created.

## Customizing Your Lambda Function
If you'd like to add support for another blog site, customize the way emails are posted to your blog, or further customize your Lambda function, open the [AWS Lambda Console](https://console.aws.amazon.com/lambda/home#/functions) to edit and test your Lambda function with the built-in code editor. For more information, see this [documentation](https://docs.aws.amazon.com/lambda/latest/dg/code-editor.html).

For more advanced use cases, such as changing your CloudFormation template to create additional AWS resources that will support this application, follow the instructions below.

## Access Control
By default, this serverless application and the resources that it creates can integrate with any [WorkMail Organization](https://docs.aws.amazon.com/workmail/latest/adminguide/organizations_overview.html) in your account, but the application and organization must be in the same region. To restrict that behavior you can either update the SourceArn attribute in [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-wordpress-python/template.yaml)
and then deploy the application by following the steps below **or** update the SourceArn attribute directly in the resource policy of each resource via their AWS Console after the deploying this application, [see example](https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html).

For more information about the SourceArn attribute, [see this documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-sourcearn).

## Local Development and Testing
Clone this repository from [GitHub](https://github.com/aws-samples/amazon-workmail-lambda-templates).

If you are not familiar with CloudFormation templates, see [Learn Template Basics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/gettingstarted.templatebasics.html).

1. Create additional resources for your application by changing [template.yaml](https://github.com/aws-samples/amazon-workmail-lambda-templates/blob/master/workmail-wordpress-python/template.yaml). For more information, see this [documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html).
2. Modify your Lambda function by changing [app.py](https://github.com/aws-samples/amazon-workmail-lambdas-templates/blob/master/workmail-wordpress-python/src/app.py).
3. Test your Lambda function locally:
 1. [Set up the SAM CLI](https://aws.amazon.com/serverless/sam/).
 2. Configure environment variables at `tst/env_vars.json`.
 3. Configure test event at `tst/event.json`.
 4. Invoke your Lambda function locally using:
        `sam local invoke WorkMailBlogPosterFunction -e tst/event.json --env-vars tst/env_vars.json`

### Test Message Ids
This application uses a `messageId` passed to the Lambda function to retrieve the message content from WorkMail. When testing, the `tst/event.json` file uses a mock messageId which does not exist. If you want to test with a real messageId, you can configure a WorkMail Email Flow Rule with the Lambda action that uses the Lambda function created in **Setup**, and send some emails that will trigger the email flow rule. The Lambda function will emit the messageId it receives from WorkMail in the CloudWatch logs, which you can
then use in your test event data. For more information see [Accessing Amazon CloudWatch logs for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs.html). Note that you can access messages in transit for a maximum of one day.

Once you have validated that your Lambda function behaves as expected, you are ready to deploy this Lambda function.

### Deploying
This step bundles all your code, dependencies and configuration to the given S3 bucket.

```bash
sam build
```

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
  --parameter-overrides SecretId=$SECRET_ID BlogDomain=$BLOG_DOMAIN \
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
