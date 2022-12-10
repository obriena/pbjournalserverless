from __future__ import print_function
import json
import datetime
import dateutil.tz
import uuid
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr

PBJSessionsTableName = "InfrastructureStack-PBJSessionsB35B5F37-RSH6RR1H4LIF"
PBJUsersTableName    = "InfrastructureStack-PBJUsers4F5D3B04-1CS9RG2F0VEJR"

def lambda_handler(event, context):
    central = dateutil.tz.gettz('US/Central')
    ct = datetime.datetime.now(tz=central)
    ts = ct.timestamp()

    print("Current Time = ", ct)

    print("Validate Save user")
    #print("Received event: " + json.dumps(event, indent=2))

    bodyStr = event['body']
    body = json.loads(bodyStr)
    print(body['email'])

    dynamoClient = boto3.client('dynamodb')

    aUser = dynamoClient.get_item(
        TableName=PBJUsersTableName,
        Key={
            'id': {'S': body['email']}
        }
    )
    print("aUser: ")
    print("Is a good user: ", ('Item' in aUser))
    print (json.dumps(aUser, indent=2))

    if ('Item' in aUser):
        print ('Found user')
    else:
        dynamoClient.put_item(
            TableName=PBJUsersTableName,
            Item={
                'id': {'S': body['email']},
                'email': {'S': body['email']},
                'lastName': {'S': body['lastName']},
                'firstName': {'S': body['firstName']},
                'profilePic': {'S': body['profilePic']},
                'authSource': {'S': body['authSource']}
            }
        )
    try:
        print("Updating valid flag in session table")
        dynamoClient.update_item(
            TableName=PBJSessionsTableName,
            Key={'email': body['email'], 'valid': 'Y'},
            UpdateExpression="set valid = :val",
            ExpressionAttributeValues={':val': str('N')},
            ReturnValues="UPDATED_NEW")
    except ClientError as err:
        logger.error(
            "Couldn't update valid flag in session table. Here's why: %s: %s",
            err.response['Error']['Code'], err.response['Error']['Message'])
   
    # newSessionValid = str("Y")
    # aSession = dynamoClient.query(
    #     TableName=PBJSessionsTableName,
    #     IndexName="email-index",
    #     KeyConditionExpression=Key('email').eq(body['email'])
    # )
    # print("aSession: ")
    # print(aSession)
    # if ('Item' in aSession):
    #     dynamoClient.update_item(
    #         TableName=PBJSessionsTableName,
    #         Key={
    #             'id': {'S': aSession['id']},
    #             'sessionId': {'S': aSession['sessionId']}
    #         },
    #         UpdateExpression="SET valid = :v",
    #         ExpressionAttributeValues={
    #             ':v': {'S': 'N'}
    #         }
    #     )

    sessionId = str(uuid.uuid4())

    dynamoClient.put_item(
        TableName=PBJSessionsTableName,
        Item={
            'id': {'S': sessionId},
            'email': {'S': body['email']},
            'valid': {'S': 'Y'},
            'createTime' : {'S': str(ts)}
        }
    )

    return {
        "message": "hello " + body['firstName'],
        "status": "success",
        "extra" : sessionId
    }