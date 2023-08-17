#!/usr/bin/env python3

from organization import Organization
from sts import create_boto3_client, assume_role
import logging
import boto3
import os
import json

loglevel = os.environ['LogLevel']
logger = logging.getLogger('logger')
logger.setLevel(level=loglevel)
sqs_queue_url = os.environ['SqsQueueUrl']

sqs = boto3.client('sqs')


def tagresources(tagkey, tagvalue, list, client):
    for line in list:
        logger.info(f'Tagging {line}')
        try:
            response = client.tag_resources(
                ResourceARNList=[line], Tags={tagkey: tagvalue})
            logger.debug(f'Response: {response}')
        except Exception as ce:
            logger.debug(f'Exception tagging resource {line}: {ce}')
            pass


def get_resources_to_tag(map, tagkey, tagvalue):
    resourcelist = []
    for resource in map:
        logger.debug(f'Resource: {resource}')
        if resource['ResourceARN'].startswith('arn:aws:cloudformation'):
            logger.debug(
                f'Resource {resource} is a cloudformation stack, we do not need to tag it')
            continue
        to_be_tagged = True
        for tag in resource['Tags']:
            if tag['Key'] == tagkey and tag['Value'] == tagvalue:
                to_be_tagged = False
                logger.debug(
                    f'Found tag {tagkey} with value {tagvalue} in resource, no need to retag')
                break
        if to_be_tagged == True:
            logger.debug(
                f'NOT FOUND tag {tagkey} with value {tagvalue} in resource, need to tag')
            resourcelist.append(resource['ResourceARN'])
    return resourcelist


def handler(event, context):

    try:
        for record in event['Records']:
            account_id = record['messageAttributes']['Account']['stringValue']
            tags_raw = record['messageAttributes']['Tags']['stringValue']
            reg = record['messageAttributes']['Region']['stringValue']
            receipt_handle = record['receiptHandle']
            tags = json.loads(tags_raw)['Tags']
    except Exception as e:
        logger.error(e)
        raise e

    for tag in tags:

        tagkey = tag['tagkey']
        tagvalue = tag['tagvalue']

        try:
            client = create_boto3_client(
                account_id, 'resourcegroupstaggingapi', assume_role(account_id), reg)
            map = client.get_resources(ResourcesPerPage=50)

            list = get_resources_to_tag(
                map['ResourceTagMappingList'], tagkey, tagvalue)
            logger.debug(
                f'List of resources to tag with key {tagkey} in {account_id} in region {reg}: {list}')

            try:
                tagresources(tagkey, tagvalue, list, client)
            except Exception as ce:
                logger.error(
                    f'Exception tagging resources in account {account_id} in region {reg}: {ce}')
                pass

            while 'PaginationToken' in map and map['PaginationToken']:
                token = map['PaginationToken']
                map = client.get_resources(
                    ResourcesPerPage=50, PaginationToken=token)
                list = get_resources_to_tag(
                    map['ResourceTagMappingList'], tagkey, tagvalue)
                logger.debug(
                    f'List of other resources to tag in {account_id} in region {reg}: {list}')
                try:
                    tagresources(tagkey, tagvalue, list, client)
                except Exception as ce:
                    logger.error(
                        f'Exception tagging resources in account {account_id} in region {reg}: {ce}')
                    pass

        except Exception as ce:
            logger.error(
                f'Exception retreiving resources in account {account_id} in region {reg}: {ce}')
            pass

    try:
        sqs.delete_message(
            QueueUrl=sqs_queue_url,
            ReceiptHandle=receipt_handle
        )
    except Exception as ce:
        logger.error(
            f'Error deleting message from queue: {ce}')

    return "Done!"
