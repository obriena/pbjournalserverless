package com.myorg;

import software.constructs.Construct;

import java.io.File;
import java.util.Arrays;
import java.util.List;

import software.amazon.awscdk.RemovalPolicy;
import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.apigateway.LambdaRestApi;
import software.amazon.awscdk.services.cloudfront.Behavior;
import software.amazon.awscdk.services.cloudfront.CloudFrontWebDistribution;
import software.amazon.awscdk.services.cloudfront.S3OriginConfig;
import software.amazon.awscdk.services.cloudfront.SourceConfiguration;
import software.amazon.awscdk.services.dynamodb.Table;
import software.amazon.awscdk.services.iam.Effect;
import software.amazon.awscdk.services.iam.PolicyStatement;
import software.amazon.awscdk.services.lambda.Code;
import software.amazon.awscdk.services.lambda.CodeSigningConfig;
import software.amazon.awscdk.services.lambda.Function;
import software.amazon.awscdk.services.lambda.Runtime;
import software.amazon.awscdk.services.s3.Bucket;
import software.amazon.awscdk.services.signer.Platform;
import software.amazon.awscdk.services.signer.SigningProfile;
import software.amazon.awscdk.services.dynamodb.Attribute;
import software.amazon.awscdk.services.dynamodb.AttributeType;
import software.amazon.awscdk.services.dynamodb.GlobalSecondaryIndexProps;

public class InfrastructureStack extends Stack {
    private static final String RESOURCES = "src/main/resources";

    public InfrastructureStack(final Construct scope, final String id) {
        this(scope, id, null);
    }

    public InfrastructureStack(final Construct scope, final String id, final StackProps props) {
        super(scope, id, props);

        createUserInterfaceArchitecture();
        Function validateSaveFunction = createValidateSaveFunction();
        LambdaRestApi.Builder.create(this, "Endpoint")
            .handler(validateSaveFunction)
            .build();

    }

    private Function createValidateSaveFunction() {
        String resourcesDir = deriveResourcesDirectory();

        PolicyStatement adminDynamoPolicy =  PolicyStatement.Builder.create()
            .actions(Arrays.asList( "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan","dynamodb:UpdateItem","dynamodb:PutItem"))
            .resources(Arrays.asList("*"))
            .effect(Effect.ALLOW)
            .build();
        
        SigningProfile codeProfile = SigningProfile.Builder.create(this, "CodeSigningProfile")
            .platform(Platform.AWS_LAMBDA_SHA384_ECDSA)
            .build();

        CodeSigningConfig config = CodeSigningConfig.Builder.create(this, "CodeSigningConfigDynamo")
            .signingProfiles(Arrays.asList(codeProfile))
            .build();
            
        Function function = Function.Builder.create(this, "DynamoFunction")
            .codeSigningConfig(config)
            .runtime(Runtime.PYTHON_3_9)
            .handler("validate_save_user_function.lambda_handler")
            .code(Code.fromAsset(resourcesDir))
            .build();
        function.addToRolePolicy(adminDynamoPolicy);

        return function;


    }

    private void createUserInterfaceArchitecture(){
        // The code that defines your stack goes here
        Bucket uiBucket = Bucket.Builder.create(this, "pbjournal")
        .versioned(true)
        .removalPolicy(RemovalPolicy.DESTROY)
        .autoDeleteObjects(true)
        .publicReadAccess(true)
        .websiteIndexDocument("index.html")
        .websiteErrorDocument("error.html")
        .build();

        S3OriginConfig s3OriginConfig = S3OriginConfig.builder()
        .s3BucketSource(uiBucket)
        .build();

        Behavior behavior = Behavior.builder().isDefaultBehavior(true).build();
        List<Behavior> behaviorList = Arrays.asList(behavior);

        SourceConfiguration sourceConfiguration = SourceConfiguration.builder().s3OriginSource(s3OriginConfig).behaviors(behaviorList).build();
        List<SourceConfiguration> sourceConfigurations = Arrays.asList(sourceConfiguration);

        CloudFrontWebDistribution cfwd = CloudFrontWebDistribution.Builder.create(this, "pbjournal-cf")
        .originConfigs(sourceConfigurations)
        .build();

        Table userTable = Table.Builder.create(this, "PBJUsers")
        .partitionKey(Attribute.builder().name("id").type(AttributeType.STRING).build())
        .build();

        Table sessionTable = Table.Builder.create(this, "PBJSessions")
        .partitionKey(Attribute.builder().name("id").type(AttributeType.STRING).build())
        .sortKey(Attribute.builder().name("email").type(AttributeType.STRING).build())
        .sortKey(Attribute.builder().name("valid").type(AttributeType.STRING).build())
        .build();

        // GlobalSecondaryIndexProps emailIndexProp = GlobalSecondaryIndexProps.builder()
        // .indexName("email-index")
        // .partitionKey(Attribute.builder().name("id").type(AttributeType.STRING).build())
        // .sortKey(Attribute.builder().name("email").type(AttributeType.STRING).build())
        // .build();

        // sessionTable.addGlobalSecondaryIndex(emailIndexProp);

    }

    private String deriveResourcesDirectory(){
        File f = new File(".");
        String resourcesDir = f.getAbsolutePath().substring(0, f.getAbsolutePath().length() - 2) + File.separator + RESOURCES;
        return resourcesDir;
    }
}
