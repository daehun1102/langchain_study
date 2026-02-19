package com.ncs.backend.controller;

import com.ncs.backend.dto.ChatRequest;
import com.ncs.backend.dto.ChatResponse;
import com.ncs.backend.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @PostMapping("/chat")
    public ResponseEntity<ChatResponse> chat(@RequestBody ChatRequest req) {
        ChatResponse response = chatService.chat(req);
        return ResponseEntity.ok(response);
    }
}
