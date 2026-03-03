package com.sdi.chatbot.controller;

import com.sdi.chatbot.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/sessions")
@RequiredArgsConstructor
public class SessionController {

    private final ChatService chatService;

    @GetMapping("/bg-status/{taskId}")
    public ResponseEntity<Object> getBgStatus(@PathVariable String taskId) {
        return ResponseEntity.ok(chatService.getBgStatus(taskId));
    }
}
