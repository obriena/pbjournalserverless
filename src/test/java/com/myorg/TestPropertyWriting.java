package com.myorg;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.Properties;

public class TestPropertyWriting {

    @BeforeAll
    public static void setup (){

    }

    @Test
    public void testProps(){
        Properties props = new Properties();
        props.setProperty("new", "property");
        InfrastructureStack.writePropertiesToLambdaConfig(props);

    }
}
