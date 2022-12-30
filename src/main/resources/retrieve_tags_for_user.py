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


PBJTagsTableName      = "InfrastructureStack-PBJTags636C4DA2-MQ2VYHKLEFHD"
PBJUsersTagsTableName = "InfrastructureStack-PBJUsersTagsE5F16220-Z4WWK9TR5ND9"
dynamoClient = boto3.client('dynamodb')

#Retrieve tags without the count performas at about 750ms on a cold query and around 450ms on subsequent queries  - this is with 8 tags
#adding a count to the tags will bean that every tag we have we will add a query to count the notes with the tag
# Performance impact is as follows:
# cold query with count:  1.35 seconds
# subsequent query with count: 650 milli seconds

def lambda_handler(event, context):
    central = dateutil.tz.gettz('US/Central')
    ct = datetime.now(tz=central)
    ts = ct.timestamp()

    print("Current Time = ", ct)
    sessionId = event['headers']['id']
    user = event['headers']['userid']

    sessionValid = session_validation_layer.validate_session(user, sessionId)

    payload= {'validSession': sessionValid}
    enableTagCount = True
    if (sessionValid):
        try:
            print('Valid Session/user')
            userTags = dynamoClient.get_item(
                TableName=PBJUsersTagsTableName,
                Key={
                    'id': {'S': user}
                }
            )
            tagsForUser=[]
            if ('Item' in userTags):
                print("Found tags for user: ", user)
                tags = userTags['Item']['tags']['L']
                for tag in tags:
                    count = 0
                    if (enableTagCount):
                        #add the count to the tag
                        tagsWithNoteIds = dynamoClient.get_item(
                            TableName=PBJTagsTableName,
                            Key={
                                'id': {'S': user},
                                'tag': {'S': tag['S']}
                            }
                        )
                        if ('Item' in tagsWithNoteIds):
                            count = len(tagsWithNoteIds['Item']['noteIds']['L'])

                    print(tag['S'])
                    tagsForUser.append(tag['S'] + " (" + str(count) + ")" )
                
                sortedTags = sorted(tagsForUser)
                print("Number of tags found: ", len(tags))
                payload['extra'] = sortedTags
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