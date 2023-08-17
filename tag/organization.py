#!/usr/bin/env python3

import boto3


class Organization:

    def __init__(self):
        """Initialise the boto3 organisation session"""
        self._org_client = boto3.client('organizations')

    def list_accounts(self):
        """Retrieves all accounts in organization."""
        existing_accounts = [
            account
            for accounts in self._org_client.get_paginator("list_accounts").paginate()
            for account in accounts['Accounts']
        ]
        return existing_accounts

    def get_account_tags(self, account_id):
        formatted_tags = self._org_client.list_tags_for_resource(
            ResourceId=account_id)
        return formatted_tags
