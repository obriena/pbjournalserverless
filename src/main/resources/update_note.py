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

PBJNotesTableName        = "InfrastructureStack-PBJNotesA2A9A042-8RUXMDXA8I00"
PBJTagsTableName         = "InfrastructureStack-PBJTags636C4DA2-MQ2VYHKLEFHD"
PBJUsersTagsTableName    = "InfrastructureStack-PBJUsersTagsE5F16220-Z4WWK9TR5ND9"

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
        bodyStr = event['body']
        body = json.loads(bodyStr)
        noteId = body['noteId']
        newContent =  body['content']
        newTagString = body['labels']

        savedNote = dynamoClient.get_item(
            TableName=PBJNotesTableName,
            Key={
                'id': {'S': noteId}
            }
        )

        #The biggest challenge here is maintaining the tags. 
        # Let's see if there are any changes to account for.
        print("Searching for user tags by user id: ", user)
        usersTags = dynamoClient.get_item(
            TableName=PBJUsersTagsTableName,
            Key={
                'id': {'S': user}
            }
        )
        tagsForUser = []
        tagsDataStructs = []
        if ('Item' in usersTags):
            #  Add tag to the list of tags
            print("User Tags Found")
            print(usersTags['Item'])
            tags = usersTags['Item']['tags']['L'] 
            tagsDataStructs = tags
            for aTag in tags:
                theTag =  aTag['S']
                tagsForUser.append(theTag)
        else:
            print("No User Tags Found")

        #NewTagString is coming from the user. It is a comma or semi-colon separated list of tags.
        splitNewTags = newTagString.split(',')
        if (len(splitNewTags) == 1):
            splitNewTags = newTagString.split(';')
        newTagsList = []
        savedTagsList = []
        for aTag in splitNewTags:
            aTag = aTag.strip()
            aTag = aTag.replace("#", '')
            newTagsList.append(aTag)

        tags = savedNote['Item']['tags']['S']
        splitTags = tags.split(',')
        if (len(splitTags) == 1):
            splitTags = tags.split(';')
        for aTag in splitTags:
            aTag = aTag.strip()
            aTag = aTag.replace("#", '')
            savedTagsList.append(aTag)
        
        #Now we have two lists of tags. One is the new tags, the other is the saved tags.
        # We need to compare the two lists and determine if there are any changes.

        #First, let's do a quick validation to see that we have all of the tags the user is submitting in our "usersTags" table.
        for tagFromUserReq in newTagsList:
            if (tagFromUserReq not in tagsForUser):
                tagsDataStructs.append({'S': tagFromUserReq})
                print("Adding tag to usersTags: ", tagFromUserReq)

                dynamoClient.update_item(
                    TableName=PBJUsersTagsTableName,
                    Key={
                        'id':{'S':user}
                    },
                    UpdateExpression="Set #theTags = list_append(#theTags, :newTag)",
                    ExpressionAttributeNames={'#theTags':'tags'},
                    ExpressionAttributeValues={
                        ":newTag":{'L':[{'S':tagFromUserReq}]}
                    }
                )

        tagsToSave = []
        tagsToDelete = []
        for aTag in newTagsList:
            if (aTag not in savedTagsList):
                tagsToSave.append(aTag)
        for aTag in savedTagsList:
            if (aTag not in newTagsList):
                tagsToDelete.append(aTag)
        print ("Tags to Save: ", len(tagsToSave))
        print ("Tags to Delete: ", len(tagsToDelete))

        #Save the new tags tied to this note
        for aTag in newTagsList:
            if (aTag not in tagsForUser):
                tagsDataStructs.append({'S': aTag})
            
            savedTag = dynamoClient.get_item(
                TableName=PBJTagsTableName,
                Key={
                    'id': {'S': user},
                    'tag': {'S': aTag}
                }
            )
            #The tag already existed
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
                        ":aNoteId":{'L':[{'S':noteId}]}
                    }
                )
            else:
                #This user does not have this tag
                #First save the tag with the noteId
                dynamoClient.put_item(
                    TableName=PBJTagsTableName,
                    Item={
                        'id': {'S':user},
                        'tag': {'S': aTag},
                        'noteIds':{'L':[{'S':noteId}]}
                    }
                )
        #Looping over the tags that need to be removed from this note
        #  However in the removing of the tag, we do need to make sure that 
        #  If there are no notes for the tag we delete the tag and the reference in the usertags table
        for aTag in tagsToDelete:
            savedTag = dynamoClient.get_item(
                TableName=PBJTagsTableName,
                Key={
                    'id': {'S': user},
                    'tag': {'S': aTag}
                }
            )
            #The tag already existed
            if ('Item' in savedTag):
                #Remove the noteId from the list
                tagNoteIds = savedTag['Item']['noteIds']['L']
            
                for nId in tagNoteIds:
                    theId = nId['S']
                    #Removing the note Id from the the list of ID's
                    if (theId == noteId):
                        tagNoteIds.remove(nId)
                        break
                if (len(tagNoteIds) == 0):
                    #Delete the tag from the usersTags table
                    freshUserTags = dynamoClient.get_item(
                        TableName=PBJUsersTagsTableName,
                        Key={
                            'id':{'S':user}
                        }
                    )
                    if ('Item' in freshUserTags):
                        freshTags = freshUserTags['Item']['tags']['L']
                        for i in range(len(freshTags)):
                            freshTag = freshTags[i]
                            theTag = freshTag['S']
                            if (theTag == aTag):
                                dynamoClient.update_item(
                                    TableName=PBJUsersTagsTableName,
                                    Key={
                                        'id':{'S':user}
                                    },
                                    UpdateExpression="REMOVE tags["+str(i)+"]",
                                )
                                break
                    
                    dynamoClient.delete_item(
                        TableName=PBJTagsTableName,
                        Key={
                            'id': {'S': user},
                            'tag': {'S': aTag}
                        }
                    )

                else:
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
            #else I don't think there should be an else condition here

    #At this point we have updated the tags now it should be just a simple update on the note itself
    print("After updating all of the tags, nowe we're updating the note itself")
    dynamoClient.update_item(
        TableName=PBJNotesTableName,
        Key={
            'id': {'S': noteId}
        },
        UpdateExpression="set content = :c, tags = :t, lastEditTime = :l",
        ExpressionAttributeValues={ ':c': {'S': newContent}, 
                                    ':t': {'S': newTagString}, 
                                    ':l': {'S': str(datetime.now().timestamp())}}
    )

    response = {
        'isBase64Encoded': False,
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Id, Content-Type, Origin, X-Auth-Token, X-Amz-Date, Authorization, X-Api-Key',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'PUT, OPTIONS',
            'Id': sessionId,
            'Content-Type': "application/json",
            'Access-Control-Expose-Headers': 'Id'
        },
        'body': json.dumps(payload)
    }
    return response