package com.myorg;

import software.constructs.Construct;
import software.amazon.awscdk.RemovalPolicy;
import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.cloudfront.CloudFrontWebDistribution;
// import software.amazon.awscdk.Duration;
// import software.amazon.awscdk.services.sqs.Queue;
import software.amazon.awscdk.services.s3.Bucket;

public class InfrastructureStack extends Stack {
    public InfrastructureStack(final Construct scope, final String id) {
        this(scope, id, null);
    }

    public InfrastructureStack(final Construct scope, final String id, final StackProps props) {
        super(scope, id, props);

        // The code that defines your stack goes here
        Bucket uiBucket = Bucket.Builder.create(this, "pbjournal")
            .versioned(true)
            .removalPolicy(RemovalPolicy.DESTROY)
            .autoDeleteObjects(true)
            .publicReadAccess(true)
            .websiteIndexDocument("index.html")
            .websiteErrorDocument("error.html")
            .build();

        CloudFrontWebDistribution cfwd = CloudFrontWebDistribution.Builder.create(this, "pbjournal-cf")
            .originConfigs(new CloudFrontWebDistribution.OriginConfig[]{
                CloudFrontWebDistribution.OriginConfig.builder()
                    .s3OriginSource(CloudFrontWebDistribution.S3OriginConfig.builder()
                        .s3BucketSource(uiBucket)
                        .originAccessIdentity(CloudFrontWebDistribution.OriginAccessIdentity.fromOriginAccessIdentityName(this, "pbjournal-cf-oai", "pbjournal-cf-oai"))
                        .build())
                    .behaviors(new CloudFrontWebDistribution.Behavior[]{
                        CloudFrontWebDistribution.Behavior.builder()
                            .isDefaultBehavior(true)
                            .build()
                    })
                    .build()
            })
            .build();
    }
}
