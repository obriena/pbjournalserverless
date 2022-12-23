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
    user      = event['headers']['userid']

    sessionValid = session_validation_layer.validate_session(user, sessionId)
    payload= {'message': sessionValid,
              'status': 'success',
              'extra':''
              }

    if (sessionValid):
        newNoteId = str(uuid.uuid4())
        bodyStr = event['body']
        body = json.loads(bodyStr)
        #  {'content': 'test message', 'labels': 'testTag'}

        # Save the new note 
        ts = str(datetime.now().timestamp())

        dynamoClient.put_item (
            TableName=PBJNotesTableName,
            Item={
                'id':{'S':newNoteId},
                'userId':{'S':user},
                'content':{'S':body['content']},
                'tags':{'S': body['labels']},
                'parentNoteId':{'S':''},
                'createTime':{'S':ts},
                'lastEditTime':{'S':ts}
            }
        )

        #Retrieve the list of notes for this user
        userNotes = dynamoClient.get_item(
            TableName=PBJUserNotesTableName,    
            Key={
                'id': {'S': user}
            }
        )
        if ('Item' in userNotes):
            #  Add noteId to the list of note Ids
            print("User Notes Found")
            print(userNotes['Item'])
            notes = userNotes['Item']['noteIds']['L']
            print(notes)
            notes.append({'S': newNoteId})
            
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
        else:
            # No notes for this user so add a new list with our new note 
            #    In it
            dynamoClient.put_item(
                TableName=PBJUserNotesTableName,
                Item={
                    'id': {'S':user},
                    'noteIds':{'L':[{'S':newNoteId}]}
                }
            )
        #Now save tags in a similar way
        # 1) Search for the tag in the Tags table PK: user (email) + tag
        # 2) If a record is found 
              # add the noteId to the list of Notes in the tag
        # 3) If the tag doesn't exist for the user, save the tag
        #       With the note Id in it
        
        #Retrieve the list of userTags for this user
        reqTagStr = body['labels']
        reqTags = reqTagStr.split(',')
        if (len(reqTags) == 1):
            reqTags = reqTagStr.split(';')
        for aTag in reqTags:
            aTag = aTag.strip()
            aTag = aTag.replace("#", '')

            savedTag = dynamoClient.get_item(
                TableName=PBJTagsTableName,
                Key={
                    'id': {'S': user},
                    'tag': {'S': aTag}
                }
            )
            if ('Item' in savedTag):
                #This user has tags
                #you do need to update the notes List
                dynamoClient.update_item(
                    TableName=PBJTagsTableName,
                    Key={
                        'id':{'S':user},
                        'tag':{'S':aTag}
                    },
                    UpdateExpression="Set #theNoteIds = list_append(#theNoteIds, :aNoteId)",
                    ExpressionAttributeNames={'#theNoteIds':'noteIds'},
                    ExpressionAttributeValues={
                        ":aNoteId":{'L':[{'S':newNoteId}]}
                    }
                )
            else:
                #This user does not have this tag
                #First save the tag
                dynamoClient.put_item(
                    TableName=PBJTagsTableName,
                    Item={
                        'id': {'S':user},
                        'tag': {'S': aTag},
                        'noteIds':{'L':[{'S':newNoteId}]}
                    }
                )
    else:
        payload['status'] = 'fail'
        payload['message'] = 'Session is not valid'

    response = {
        'isBase64Encoded': False,
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Id, Content-Type, Origin, X-Auth-Token, X-Amz-Date, Authorization, X-Api-Key',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Id': sessionId,
            'Content-Type': "application/json",
            'Access-Control-Expose-Headers': 'Id'
        },
        'body': json.dumps(payload)
    }
    return response