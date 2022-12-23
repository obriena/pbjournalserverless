package com.myorg;


import software.amazon.awscdk.CfnOutput;
import software.amazon.awscdk.RemovalPolicy;
import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.apigateway.*;
import software.amazon.awscdk.services.certificatemanager.Certificate;
import software.amazon.awscdk.services.cloudfront.Behavior;
import software.amazon.awscdk.services.cloudfront.CloudFrontWebDistribution;
import software.amazon.awscdk.services.cloudfront.S3OriginConfig;
import software.amazon.awscdk.services.cloudfront.SourceConfiguration;
import software.amazon.awscdk.services.dynamodb.Attribute;
import software.amazon.awscdk.services.dynamodb.AttributeType;
import software.amazon.awscdk.services.dynamodb.Table;
import software.amazon.awscdk.services.events.targets.ApiGateway;
import software.amazon.awscdk.services.iam.Effect;
import software.amazon.awscdk.services.iam.PolicyStatement;
import software.amazon.awscdk.services.lambda.*;
import software.amazon.awscdk.services.lambda.Runtime;
import software.amazon.awscdk.services.s3.Bucket;
import software.amazon.awscdk.services.signer.Platform;
import software.amazon.awscdk.services.signer.SigningProfile;
import software.constructs.Construct;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.*;

public class InfrastructureStack extends Stack {
    private static final String RESOURCES = "src/main/resources";
    private static final String ROOT_API = "pbjservices";
    private static final String AWS_CERT_ARN = "arn:aws:acm:us-east-2:746355193120:certificate/6b22b4fb-57bf-4bf9-82e9-1a0952a2fb93";
    private final SigningProfile CODE_PROFILE = SigningProfile.Builder.create(this, "CodeSigningProfile")
            .platform(Platform.AWS_LAMBDA_SHA384_ECDSA)
            .build();

    private final CodeSigningConfig CONFIG = CodeSigningConfig.Builder.create(this, "CodeSigningConfigDynamo")
            .signingProfiles(Arrays.asList(CODE_PROFILE))
            .build();

    private final ApiGateway API_GATEWAY = ApiGateway.Builder.create(RestApi.Builder.create(this, ROOT_API).build()).build();

    public InfrastructureStack(final Construct scope, final String id) {
        this(scope, id, null);
    }

    public InfrastructureStack(final Construct scope, final String id, final StackProps props) {
        super(scope, id, props);

        createUserInterfaceArchitecture();
        createTablesForNoteManagement();

        LayerVersion layer = new LayerVersion(this, "SessionValidationLayer", LayerVersionProps.builder()
                .code(Code.fromAsset(deriveResourcesDirectory()))
                .compatibleRuntimes(List.of(Runtime.PYTHON_3_9))
                .build());
        Function validateSaveFunction  = createLambdaFunction("Login", "validate_save_user_function.lambda_handler", layer);
        Function retrieveNotesFunction = createLambdaFunction("RetrieveNotes", "retrieve_notes_for_user.lambda_handler", layer);
        Function saveNoteFunction = createLambdaFunction("SaveNote", "save_note.lambda_handler", layer);
        Function updateNoteFunction = createLambdaFunction("UpdateNote", "update_note.lambda_handler", layer);
        Function deleteNoteFunction = createLambdaFunction("DeleteNote", "delete_note.lambda_handler", layer);

        API_GATEWAY.getRestApi().addDomainName("pbjournalservices", DomainNameOptions.builder()
        .domainName("api.flyingspheres.info")
        .securityPolicy(SecurityPolicy.TLS_1_2)
        .certificate(Certificate.fromCertificateArn(this, "fsInfoCert", AWS_CERT_ARN))
        .endpointType(EndpointType.REGIONAL).build());

        //There is a manually created record in Route53 to point to this custome domain name

        buildApiGatewayMapping("user", "POST", validateSaveFunction);
        buildApiGatewayMapping("notes", "GET", retrieveNotesFunction);
        buildApiGatewayMapping("saveNote", "POST", saveNoteFunction);
        buildApiGatewayMapping("updateNote", "PUT", updateNoteFunction);
        buildApiGatewayMapping("deleteNote", "DELETE", deleteNoteFunction);

    }

    private void buildApiGatewayMapping(String endpoint, String method, Function lambdaFunction) {

        CorsOptions cors = CorsOptions.builder()
                .allowHeaders(Arrays.asList("Origin", "Content-Type", "X-Auth-Token", "X-Amz-Date", "Authorization", "X-Api-Key", "id","userid"))
                .allowOrigins(Arrays.asList("*"))
                .allowMethods(Arrays.asList("OPTIONS", method))
                .build();
        API_GATEWAY.getRestApi().getRoot()
                .resourceForPath(endpoint)
                .addMethod(method, LambdaIntegration.Builder.create(lambdaFunction)
                        .passthroughBehavior(PassthroughBehavior.WHEN_NO_TEMPLATES)
                        .requestTemplates(Map.of("application/json", "{\n" +
                                "  \"method\": \"$context.httpMethod\",\n" +
                                "  \"body\" : $input.json('$'),\n" +
                                "  \"headers\": {\n" +
                                "    #foreach($param in $input.params().header.keySet())\n" +
                                "    \"$param\": \"$util.escapeJavaScript($input.params().header.get($param))\"\n" +
                                "    #if($foreach.hasNext),#end\n" +
                                "    #end\n" +
                                "  }\n" +
                                "}"))
                        .build());
        API_GATEWAY.getRestApi().getRoot().resourceForPath(endpoint).addCorsPreflight(cors);
        CfnOutput.Builder.create(this, "HTTP API URL").value(API_GATEWAY.getRestApi().getUrl());
    }

    private Function createLambdaFunction(String lambdaName, String pythonLambdaName, LayerVersion layer) {
        String resourcesDir = deriveResourcesDirectory();

        PolicyStatement adminDynamoPolicy =  PolicyStatement.Builder.create()
            .actions(Arrays.asList( "dynamodb:GetItem", "dynamodb:Query", "dynamodb:UpdateItem","dynamodb:PutItem"))
            .resources(Arrays.asList("*"))
            .effect(Effect.ALLOW)
            .build();

        Function function = Function.Builder.create(this, lambdaName)
            .codeSigningConfig(CONFIG)
            .runtime(Runtime.PYTHON_3_9)
            .handler(pythonLambdaName)
            .code(Code.fromAsset(resourcesDir))
            .layers(List.of(layer))
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

        String userTableName = buildUserTable();
        String activeSessionTableName = buildActiveSessionTable();
        String sessionHistoryTableName = buildSessionHistoryTable();

        Properties props = new Properties();
        props.setProperty("userTableName", userTableName);
        props.setProperty("activeSessionTable", activeSessionTableName);
        props.setProperty("sesionHistoryTableNam", sessionHistoryTableName);

        writePropertiesToLambdaConfig(props);
    }

    private void createTablesForNoteManagement() {
        String userNotesTable = buildTable("PBJUsersNotes");
        //String userTagsTable  = buildTable("PBJUsersTags");
        String noteTable      = buildTable("PBJNotes");

        //Tags Table
        Table tagsTable = Table.Builder.create(this, "PBJTags")
                .partitionKey(Attribute.builder().name("id").type(AttributeType.STRING).build())
                .sortKey(Attribute.builder().name("tag").type(AttributeType.STRING).build())
                .removalPolicy(RemovalPolicy.DESTROY)
                .build();
    }

    private String buildActiveSessionTable() {
        return buildTable("PBJActiveSessions");
    }
    private String buildSessionHistoryTable() {
        return buildTable("PBJSessions");
    }
    private String buildUserTable() {
        return buildTable("PBJUsers");
    }

    private String buildTable(String tableName){
        Table sessionTable = Table.Builder.create(this, tableName)
                .partitionKey(Attribute.builder().name("id").type(AttributeType.STRING).build())
                .removalPolicy(RemovalPolicy.DESTROY)
                .build();
        return sessionTable.getTableName();
    }

    protected static void writePropertiesToLambdaConfig(Properties props) {
        File f = new File(".");
        String absPath = f.getAbsolutePath();
        absPath = absPath.substring(0, absPath.length() -1);

        String outPutPath = absPath + "src/main/resources/";
        String fileName = "env.props";
        System.out.println(outPutPath);

        try {
            FileOutputStream fos = new FileOutputStream(new File(outPutPath + fileName));
            props.store(fos, "Environment Variables for lambda functions");
        } catch (FileNotFoundException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }

    }

    private String deriveResourcesDirectory(){
        File f = new File(".");
        String resourcesDir = f.getAbsolutePath().substring(0, f.getAbsolutePath().length() - 2) + File.separator + RESOURCES;
        return resourcesDir;
    }
}
