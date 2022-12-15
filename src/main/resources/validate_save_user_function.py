from __future__ import print_function
import json
import datetime
import dateutil.tz
import uuid
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr


PBJActiveSessionsTableName = "InfrastructureStack-PBJActiveSessions8DE764BB-BZOEKCXZOO66"
PBJSessionHistoryTableName = "InfrastructureStack-PBJSessionsB35B5F37-D22MMSNCON12"
PBJUsersTableName    = "InfrastructureStack-PBJUsers4F5D3B04-179SG4K8B4VB5"
dynamoClient = boto3.client('dynamodb')

def lambda_handler(event, context):
    central = dateutil.tz.gettz('US/Central')
    ct = datetime.datetime.now(tz=central)
    ts = ct.timestamp()

    print("Current Time = ", ct)

    print("Validate Save user")

    bodyStr = event['body']
    body = json.loads(bodyStr)

    aUser = dynamoClient.get_item(
        TableName=PBJUsersTableName,
        Key={
            'id': {'S': body['email']}
        }
    )

    sessionId = str(uuid.uuid4())
    if ('Item' in aUser):
        print ('Found user')
        # retrieve the active session and update the sessionId
        # retrieve the session history and update the lastAccess to match the old lastAccess time
        # finally update the session in the active ssessions table with a new session, create time and last access time
        actSessin = dynamoClient.get_item(
            TableName=PBJActiveSessionsTableName,
            Key={
                'id': {'S': body['email']}
            }
        )
        if ('Item' in actSessin):
            #update last access in history
            histSession = dynamoClient.update_item(
                TableName=PBJSessionHistoryTableName,
                Key={
                    'id': {'S': actSessin['Item']['sessionId']['S']}
                },
                UpdateExpression="set lastAccess = :la",
                ExpressionAttributeValues={
                    ':la': {'S': actSessin['Item']['lastAccess']['S']}
                },
                ReturnValues="UPDATED_NEW"
            )

            #Update active session with new session Id
            dynamoClient.update_item(
                TableName=PBJActiveSessionsTableName,
                Key={
                    'id': {'S': body['email']}
                },
                UpdateExpression="set sessionId = :s, lastAccess = :la, createTime = :ct",
                ExpressionAttributeValues={
                    ':s': {'S': sessionId},
                    ':la': {'S': str(ts)},
                    ':ct': {'S': str(ts)}
                },
                ReturnValues="UPDATED_NEW"
            )
            #save new session in history
            dynamoClient.put_item(
            TableName=PBJSessionHistoryTableName,
            Item={
                'id': {'S': sessionId},
                'email': {'S': body['email']},
                'createTime' : {'S': str(ts)},
                'lastAccess' : {'S': str(ts)}
            }
    )
        else:
            saveNewSessionData(sessionId, body['email'], str(ts))         
    else:
        #This is a new user.  Create a record in the PBJUsers table, and a record in the PBJActiveSessions table, and a record in the PBJSessions table
        dynamoClient.put_item(
            TableName=PBJUsersTableName,
            Item={
                'id': {'S': body['email']},
                'email': {'S': body['email']},
                'lastName': {'S': body['lastName']},
                'firstName': {'S': body['firstName']},
                'profilePic': {'S': body['profilePic']},
                'authSource': {'S': body['authSource']},
                'createTime' : {'S': str(ts)}
            }
        )
        saveNewSessionData(sessionId, body['email'], str(ts))
    payload = {
                  "message": "hello " + body['firstName'],
                  "status": "success",
                  "extra" : sessionId
              }
    response = {
        'isBase64Encoded': False,
        'statusCode': 200,
        'headers': {
            'Content-Type': "application/json"
        },
        'body': json.dumps(payload)
    }
    return response


def saveNewSessionData(sessionId, email, timestamp):
    dynamoClient.put_item(
        TableName=PBJActiveSessionsTableName,
        Item={
            'id': {'S': email},
            'sessionId': {'S': sessionId},
            'createTime' : {'S': timestamp},
            'lastAccess' : {'S': timestamp}
        }
    )
    dynamoClient.put_item(
        TableName=PBJSessionHistoryTableName,
        Item={
            'id': {'S': sessionId},
            'email': {'S': email},
            'createTime' : {'S': timestamp},
            'lastAccess' : {'S': timestamp}
        }
    )