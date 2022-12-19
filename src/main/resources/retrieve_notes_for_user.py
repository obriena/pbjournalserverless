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

PBJActiveSessionsTableName = "InfrastructureStack-PBJActiveSessions8DE764BB-BZOEKCXZOO66"
dynamoClient = boto3.client('dynamodb')

def lambda_handler(event, context):
    central = dateutil.tz.gettz('US/Central')
    ct = datetime.now(tz=central)
    ts = ct.timestamp()

    print("Current Time = ", ct)
    sessionId = event['headers']['id']
    user = event['headers']['userId']

    sessionValid = session_validation_layer.validate_session(user, sessionId)

    payload = {
        "message": "hello ",
        "status": "success",
        "extra" : []
    }
    if (sessionValid):
        print('Valid Session/user')
        #Retrieve the notes
        # payload['extra'] = retrieveNotesForUser(user)
    else:
        payload['message'] = "Session Invalid"
        payload['status'] = "error"
        sessonId = 'invalid'
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