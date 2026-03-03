package com.sdi.chatbot.controller;

import com.sdi.chatbot.dto.*;
import com.sdi.chatbot.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @PostMapping("/analyze")
    public ResponseEntity<AnalyzeResponse> analyze(@RequestBody AnalyzeRequest request) {
        return ResponseEntity.ok(chatService.analyze(request));
    }

    @PostMapping("/investigate")
    public ResponseEntity<InvestigateResponse> investigate(@RequestBody InvestigateRequest request) {
        return ResponseEntity.ok(chatService.investigate(request));
    }
}
