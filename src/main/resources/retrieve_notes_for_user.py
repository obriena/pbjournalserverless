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

PBJUserNotesTableName    = "InfrastructureStack-PBJUsersNotes32044C9E-1ASYV3I7XHQ8U"
PBJNotesTableName        = "InfrastructureStack-PBJNotesA2A9A042-8RUXMDXA8I00"

PBJTagsTableName         = "InfrastructureStack-PBJTags636C4DA2-MQ2VYHKLEFHD"
dynamoClient = boto3.client('dynamodb')

def lambda_handler(event, context):
    central = dateutil.tz.gettz('US/Central')
    ct = datetime.now(tz=central)
    ts = ct.timestamp()

    print("Current Time = ", ct)

    sessionValid = False
    try:
        sessionId = event['headers']['id']
        user = event['headers']['userid']

        sessionValid = session_validation_layer.validate_session(user, sessionId)
    except:
        print("Exception working with headers:")
        print(event['headers'])

    payload = {
        "message": "hello ",
        "status": "success",
        "extra" : []
    }
    if (sessionValid):
        print('Valid Session/user')
        userNotes = dynamoClient.get_item(
            TableName=PBJUserNotesTableName,
            Key={
                'id': {'S': user}
            }
        )
        if ('Item' in userNotes):
            print("Found notes for user: ", user)
            notes = userNotes['Item']['noteIds']['L']
            print("Number of notes found: ", len(notes))
            respNotes = []
            for note in notes:
                noteId = note['S']
                print("NoteId: ", noteId)
                savedNote = dynamoClient.get_item(
                    TableName=PBJNotesTableName,
                    Key={
                        'id': {'S': noteId}
                    }
                )
                if ('Item' in savedNote):
                    thisNote = savedNote['Item']
                    print("Found note: ", thisNote)
                    content = thisNote['content']['S']
                    createTime = thisNote['createTime']['S']
                    lastEditTime = thisNote['lastEditTime']['S']
                    id= thisNote['id']['S']
                    savedTags = thisNote['tags']['S']
                    respNote = {'id':id,
                                'userId': lastEditTime,
                                'createTime': createTime,
                                'content': content,
                                'labelsAsText': savedTags
                                }
                    respNotes.append(respNote)
                    print("Response Note: ", len(respNotes))
            sortedList = sorted(respNotes, key=lambda k: k['createTime'], reverse=True)
            payload['extra'] = sortedList
    else:
        payload['message'] = "Session Invalid"
        payload['status'] = "error"
        sessonId = 'invalid'
    response = {
        'isBase64Encoded': False,
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Id, UserId, Content-Type, Origin, X-Auth-Token, X-Amz-Date, Authorization, X-Api-Key',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Id': sessionId,
            'Content-Type': "application/json",
            'Access-Control-Expose-Headers': 'Id'
        },
        'body': json.dumps(payload)
    }
    return response