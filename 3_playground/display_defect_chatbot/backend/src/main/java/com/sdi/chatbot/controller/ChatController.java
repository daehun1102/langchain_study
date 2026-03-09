package com.sdi.chatbot.controller;

import com.sdi.chatbot.dto.AgentRequest;
import com.sdi.chatbot.dto.AgentResponse;
import com.sdi.chatbot.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @PostMapping("/agent")
    public ResponseEntity<AgentResponse> agent(@RequestBody AgentRequest request) {
        return ResponseEntity.ok(chatService.agent(request));
    }

    @GetMapping("/bg-status/{taskId}")
    public ResponseEntity<Object> getBgStatus(@PathVariable String taskId) {
        return ResponseEntity.ok(chatService.getBgStatus(taskId));
    }
}
