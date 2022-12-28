from __future__ import print_function
import json
import datetime
from datetime import datetime
import dateutil.tz
import uuid
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr
import session_validation_layer


PBJTagsTableName = "InfrastructureStack-PBJTags636C4DA2-MQ2VYHKLEFHD"
dynamoClient = boto3.client('dynamodb')

def lambda_handler(event, context):
    central = dateutil.tz.gettz('US/Central')
    ct = datetime.now(tz=central)
    ts = ct.timestamp()

    print("Current Time = ", ct)
    sessionId = event['headers']['id']
    user = event['headers']['userid']

    sessionValid = session_validation_layer.validate_session(user, sessionId)

    payload= {'validSession': sessionValid}

    if (sessionValid):
        try:
            print('Valid Session/user')
            userTags = dynamoClient.get_item(
                TableName=PBJTagsTableName,
                Key={
                    'id': {'S': user}
                    'tag': 
                }
            )
            if ('Item' in userTags):
                print("Found tags for user: ", user)
                tags = userTags['Item']
                print("Number of tags found: ", len(tags))
                payload['extra'] = tags['tags']
                payload['message'] = str(len(tags))
                payload['status'] = 'success'
        except Exception as err:
            print(f"Exception working with tags: {err=}, {type(err)=}")
            payload['message'] = 'Server Error'
            payload['status'] = 'failed'
    response = {
        'isBase64Encoded': False,
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Id, Content-Type, Origin, X-Auth-Token, X-Amz-Date, Authorization, X-Api-Key',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Id': sessionId,
            'Content-Type': "application/json",
            'Access-Control-Expose-Headers': 'Id'
        },
        'body': json.dumps(payload)
    }
    return response