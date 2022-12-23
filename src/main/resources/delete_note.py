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
    sessionId = event['headers']['id']
    user = event['headers']['userid']

    sessionValid = session_validation_layer.validate_session(user, sessionId)

    payload= {'validSession': sessionValid}

    bodyStr = event['body']
    body = json.loads(bodyStr)
    noteId = body['noteId']

    savedNote = dynamoClient.get_item(
        TableName=PBJNotesTableName,
        Key={
            'id': {'S': noteId}
        }
    )

    if ('Item' in savedNote):
        savedNote = savedNote['Item']
        tags = savedNote['tags']['S']
        splitTags = tags.split(',')
        if (len(splitTags) == 1):
            splitTags = tags.split(';')
        for aTag in splitTags:
            aTag = aTag.strip()
            aTag = aTag.replace("#", '')

            #Retrieve the tag
            savedTag = dynamoClient.get_item(
                TableName=PBJTagsTableName,
                Key={
                    'id': {'S': user},
                    'tag': {'S': aTag}
                }
            )
            #Get the list of notes tied to this tag and find the one that is being deleted
            tagNoteIds = savedTag['Item']['noteIds']['L']
            
            for nId in tagNoteIds:
                theId = nId['S']
                if (theId == noteId):
                    tagNoteIds.remove(nId)
                    break

            dynamoClient.update_item(
                TableName=PBJTagsTableName,
                Key={
                    'id': {'S': user},
                    'tag': {'S': aTag}
                },
                UpdateExpression="set noteIds = :n",
                ExpressionAttributeValues={
                    ':n': {'L': tagNoteIds}
                }
            )
            #Pull back the list of userNotes and remove the noteId from the list
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
                for note in notes:
                    savedNoteId = note['S']
                    if (savedNoteId == noteId):
                        notes.remove(note)
                        dynamoClient.update_item(
                            TableName=PBJUserNotesTableName,
                            Key={
                                'id': {'S': user}
                            },
                            UpdateExpression="set noteIds = :n",
                            ExpressionAttributeValues={
                                ':n': {'L': notes}
                            }
                        )
    #Delete the note (the easy part)
    dynamoClient.delete_item(
        TableName=PBJNotesTableName,
        Key={
            'id': {'S': noteId}
        }
    )



    response = {
        'isBase64Encoded': False,
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Id, Content-Type, Origin, X-Auth-Token, X-Amz-Date, Authorization, X-Api-Key',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'DELETE, OPTIONS',
            'Id': sessionId,
            'Content-Type': "application/json",
            'Access-Control-Expose-Headers': 'Id'
        },
        'body': json.dumps(payload)
    }
    return response