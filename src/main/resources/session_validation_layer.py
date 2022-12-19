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
timeoutSeconds = 60 * 15

def validate_session(user, sessionId):
    dynamoClient = boto3.client('dynamodb')
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

    return sessionValid