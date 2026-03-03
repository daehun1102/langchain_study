package com.sdi.chatbot.service;

import com.sdi.chatbot.dto.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
@RequiredArgsConstructor
public class ChatService {

    private final RestClient aiRestClient;

    public AnalyzeResponse analyze(AnalyzeRequest request) {
        return aiRestClient.post()
                .uri("/internal/analyze")
                .body(request)
                .retrieve()
                .body(AnalyzeResponse.class);
    }

    public InvestigateResponse investigate(InvestigateRequest request) {
        return aiRestClient.post()
                .uri("/internal/investigate")
                .body(request)
                .retrieve()
                .body(InvestigateResponse.class);
    }

    public Object getBgStatus(String taskId) {
        return aiRestClient.get()
                .uri("/internal/bg-status/" + taskId)
                .retrieve()
                .body(Object.class);
    }
}
