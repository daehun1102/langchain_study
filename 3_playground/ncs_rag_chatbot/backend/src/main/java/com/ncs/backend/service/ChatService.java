package com.ncs.backend.service;

import com.ncs.backend.dto.ChatRequest;
import com.ncs.backend.dto.ChatResponse;
import com.ncs.backend.dto.InternalChatRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatService {

    private final DocumentService documentService;
    private final RestClient pythonRestClient;

    public ChatResponse chat(ChatRequest req) {
        // 1. Oracle에서 카테고리에 맞는 doc_id 목록 조회
        List<String> docIds = documentService.findDocIdsByCategory(
                req.getMainCategory(), req.getSubCategory()
        );
        log.info("[ChatService] query={}, docIds={}", req.getQuery(), docIds);

        // 2. Python AI 서버로 query + doc_ids 전달
        InternalChatRequest internalReq = new InternalChatRequest(req.getQuery(), docIds);
        ChatResponse response = pythonRestClient.post()
                .uri("/internal/chat")
                .body(internalReq)
                .retrieve()
                .body(ChatResponse.class);

        return response;
    }
}
