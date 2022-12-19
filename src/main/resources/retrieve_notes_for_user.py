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

PBJActiveSessionsTableName = "InfrastructureStack-PBJActiveSessions8DE764BB-BZOEKCXZOO66"
dynamoClient = boto3.client('dynamodb')

timeoutSeconds = 60 * 15

def lambda_handler(event, context):
    central = dateutil.tz.gettz('US/Central')
    ct = datetime.now(tz=central)
    ts = ct.timestamp()

    print("Current Time = ", ct)
    #print(event)
    sessionId = event['headers']['id']
    user = event['headers']['userId']

    #Active Session retrieves theActiveSession by the UserId
    aSession = dynamoClient.get_item(
        TableName=PBJActiveSessionsTableName,
        Key={
            'id': {'S': user}
        }
    )
    sessionValid = True
    if ('Item' in aSession):
        storedSessionId = aSession['Item']['sessionId']['S']
        print("Found active session id: ", storedSessionId)
        print("Header SessionID: ", sessionId)
        if (sessionId == storedSessionId):
            stringLastAccess = aSession['Item']['lastAccess']['S']
            #something like this: 1671400079.785493
            floatLastAccess = float(stringLastAccess)
            intLastAccess = (int(floatLastAccess))

            dateLastAccess = datetime.fromtimestamp(intLastAccess)
            now = datetime.now()
            diff = now - dateLastAccess
            seconds = diff.seconds
            print ("Age of session in seconds: ", seconds)
            if (seconds > timeoutSeconds):
                sessionValid = False
            else:
                print("Updating timestamp to: ", str(now.timestamp))
                updSession = dynamoClient.update_item(
                    TableName=PBJActiveSessionsTableName,
                    Key={
                        'id': {'S': user}
                    },
                    UpdateExpression="set lastAccess = :la",
                    ExpressionAttributeValues={
                        ':la': {'S': str(now.timestamp())}
                    },
                    ReturnValues="UPDATED_NEW"
                )
        else:
            sessionValid = False
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