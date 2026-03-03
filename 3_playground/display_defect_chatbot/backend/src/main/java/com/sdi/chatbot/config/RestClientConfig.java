package com.sdi.chatbot.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfig {

    @Value("${ai.server.url}")
    private String aiServerUrl;

    @Bean
    public RestClient aiRestClient() {
        return RestClient.builder()
                .baseUrl(aiServerUrl)
                .build();
    }
}
