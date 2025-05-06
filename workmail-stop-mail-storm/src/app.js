/* jshint node: true, esversion: 9 */
'use strict';

// this is automatically installed in your lambda environment
const { CloudWatch } = require('@aws-sdk/client-cloudwatch');
const cloudwatch = new CloudWatch(); // uses your lambda credentials to call Cloudwatch

const ALARM_PREFIX = 'EmailsReceived-';
const DEFAULT_THRESHOLD = 20; // in case environment variable THRESHOLD is missing.

async function emitNewMetric(protectedRecipients) {
    // see https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html for detailed
    // explanation of the parameters
    const params = {
        Namespace: 'WorkMail',
        MetricData: protectedRecipients.map(protectedRecipient =>
            ({
                MetricName: 'EmailsReceived',
                Dimensions: [
                    {
                        Name: 'EmailAddress',
                        Value: protectedRecipient
                    }
                ],
                Unit: 'Count',
                Value: 1
            }))
    };

    // it is important that we emit the metric even if we block this sending later
    // otherwise, the alarm would clear after 5 mins, people would be able to continue the storm for a while again
    // that would lead to a on-off-on-off pattern, which still lets too much junk through

    await cloudwatch.putMetricData(params);
    console.log('Finished putMetricData');
}

async function createMissingAlarms(alarms, protectedRecipients) {
    // find the protected addresses for which there is already an alarm
    const protectedAddressesWithAlarm = alarms.MetricAlarms
        .map(metricAlarm => metricAlarm.Dimensions[0].Value);

    // remove those from all alarms. the remaining addresses are missing alarms
    const protectedAddressesMissingAlarm = protectedRecipients
        .filter(protectedAddress => !protectedAddressesWithAlarm.includes(protectedAddress));

    // create the alarm for those
    for (let protectedAddress of protectedAddressesMissingAlarm) {
        // this will create an alarm that will fire if we receive in 3 different minutes more than THRESHOLD emails
        // per minute, in a window of the last 5 minutes.

        // see https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricAlarm.html for detailed
        // explanation of the parameters
        const params = {
            AlarmName: ALARM_PREFIX + protectedAddress,
            ComparisonOperator: 'GreaterThanThreshold',
            AlarmDescription: 'Mail storm in progress for group ' + protectedAddress,
            Dimensions: [
                {
                    Name: 'EmailAddress',
                    Value: protectedAddress
                },
            ],
            MetricName: 'EmailsReceived',
            Namespace: 'WorkMail',
            TreatMissingData: 'notBreaching',
            // The parameters below control how sensitive the detection for mailstorm is.
            DatapointsToAlarm: 3, // alarm if 3 of the last 5 datapoints are above threshold
            EvaluationPeriods: 5,
            Period: 60, // each data point for evaluation is a sum of emails received in the last 60 s.
            Statistic: 'Sum',
            // configure using the THRESHOLD lambda environment variable
            Threshold: parseInt(process.env.THRESHOLD || DEFAULT_THRESHOLD),

        };
        console.log('Creating alarm for address ' + protectedAddress);
        const alarm = await cloudwatch.putMetricAlarm(params);
        console.log(alarm);
    }
}

async function verifyAlarms(protectedRecipients) {
    // see https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_DescribeAlarms.html for detailed
    // explanation of the parameters
    const params = {
        AlarmNames: protectedRecipients.map(protectedAddress => ALARM_PREFIX + protectedAddress),
        AlarmTypes: ['MetricAlarm'],
    };

    const allAlarms = await cloudwatch.describeAlarms(params);
    console.log('Finished describeAlarms - Results:');
    console.log(allAlarms);

    const protectedAddressesInAlarm = allAlarms.MetricAlarms
        .filter(metricAlarm => metricAlarm.StateValue === 'ALARM')
        .map(metricAlarm => metricAlarm.Dimensions[0].Value);

    return {allAlarms, protectedAddressesInAlarm};
}

exports.lambdaHandler = async (event) => {
    console.log('Event received by lambda function:');
    console.log(JSON.stringify(event)); // see event documentation in https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html
    console.log('Environment variables:');
    console.log(JSON.stringify(process.env));

    // split on comma, and cleanup whitespace around
    const allProtectedAddresses = (process.env.PROTECTED_ADDRESSES || '')
        .split(',').map(address => address.trim());

    console.log('Email addresses to protect against mail storms: ' + allProtectedAddresses);

    // take only the email address of each recipient
    const recipients = event.envelope.recipients.map(recipient => recipient.address);

    // find the protected recipients among all recipients
    const protectedRecipients = recipients.filter(recipient => allProtectedAddresses.includes(recipient));

    // in this case, we can simply let the email pass, and avoid looking at all alarms
    if (protectedRecipients.length === 0) {
        console.log('No recipient in this email is protected against mail storm. Letting the email pass.');
        return {
            actions: [
                {
                    allRecipients: true,        // for all recipients
                    action: {type: 'DEFAULT'}   // let the email be sent normally
                }
            ]
        };
    }

    await emitNewMetric(protectedRecipients);
    const {allAlarms, protectedAddressesInAlarm} = await verifyAlarms(protectedRecipients);

    // an alarm can be missing for a protected address if it is the first time we receive an email for it
    await createMissingAlarms(allAlarms, protectedRecipients);

    if (protectedAddressesInAlarm.length > 0) {
        console.log('Bouncing email from ' + event.envelope.mailFrom.address + ' to ' + protectedAddressesInAlarm);
    }

    return {
        actions: [
            {
                recipients: protectedAddressesInAlarm,  // for the recipients in alarm
                action: {type: 'BOUNCE'},               // make it bounce
            },
            {
                allRecipients: true,                    // for all the other recipients
                action: {type: 'DEFAULT'},              // let the email pass normally
            }
        ]
    };
};
