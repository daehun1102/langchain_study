package com.sdi.chatbot.service;

import com.sdi.chatbot.dto.AgentRequest;
import com.sdi.chatbot.dto.AgentResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
@RequiredArgsConstructor
public class ChatService {

    private final RestClient aiRestClient;

    public AgentResponse agent(AgentRequest request) {
        return aiRestClient.post()
                .uri("/internal/agent")
                .body(request)
                .retrieve()
                .body(AgentResponse.class);
    }

    public Object getBgStatus(String taskId) {
        return aiRestClient.get()
                .uri("/internal/bg-status/" + taskId)
                .retrieve()
                .body(Object.class);
    }
}
