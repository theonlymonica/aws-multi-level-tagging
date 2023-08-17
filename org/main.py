#!/usr/bin/env python3

from organization import Organization
import logging
import boto3
import os
import json

loglevel = os.environ['LogLevel']
tagkeys = os.environ['TagKeys']
sqs_queue_url = os.environ['SqsQueueUrl']
regions_list = os.environ['RegionsList']
logger = logging.getLogger('logger')
logger.setLevel(level=loglevel)

def handler(event, context):
    organization = Organization()
    client = boto3.client('sqs')

    for account in organization.list_accounts():
        account_id = account.get('Id')

        try:
            tags = organization.get_account_tags(account_id)
        except Exception as ce:
            logger.error(
                f'Exception retrieving tags in Organization for account {account_id}: {ce}')
            continue

        response_tags = []

        for tagkey in tagkeys.split(','):
            for tag in tags["Tags"]:
                tagvalue = ''
                if tag["Key"] == tagkey:
                    tagvalue = tag["Value"]
                    logger.debug(
                        f'Found {tagkey} with value {tagvalue} in account {account_id}')

                if not tagvalue:
                    logger.debug(f'No {tagkey} found in account {account_id}')
                    continue
                else:
                    obj_tag = {
                        'tagkey':tagkey,
                        'tagvalue':tagvalue
                    }
                    response_tags.append(obj_tag)
                    break

        if len(response_tags) > 0:
            response_json = {
                'Tags' :
                    response_tags
            }
            for reg in regions_list.split(','):
                try:
                    response = client.send_message(
                        QueueUrl=sqs_queue_url,
                        DelaySeconds=15,
                        MessageAttributes={
                            'Account': {
                                'DataType': 'String',
                                'StringValue': account_id
                            },
                            'Tags': {
                                'DataType': 'String',
                                'StringValue': json.dumps(response_json)
                            },
                            'Region': {
                                'DataType': 'String',
                                'StringValue': reg
                            }
                        },
                        MessageBody=(
                            f'Tag value for account {account_id} in region {reg}'
                        )
                    )
                    logger.debug(response['MessageId'])
                except Exception as ce:
                    logger.error(
                        f'Exception sending messages to SQS for account {account_id} in region {reg}: {ce}')
                    pass

    return "Done!"
