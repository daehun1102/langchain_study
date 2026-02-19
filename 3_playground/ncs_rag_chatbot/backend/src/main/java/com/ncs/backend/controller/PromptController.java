package com.ncs.backend.controller;

import com.ncs.backend.service.PromptService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/prompts")
@RequiredArgsConstructor
public class PromptController {

    private final PromptService promptService;

    @GetMapping
    public ResponseEntity<Map<String, String>> getAll() {
        return ResponseEntity.ok(promptService.getAll());
    }

    @GetMapping("/{key}")
    public ResponseEntity<Map<String, String>> get(@PathVariable String key) {
        String value = promptService.get(key);
        if (value == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(Map.of("key", key, "value", value));
    }

    @PutMapping("/{key}")
    public ResponseEntity<Void> set(
            @PathVariable String key,
            @RequestBody Map<String, String> body) {
        promptService.set(key, body.get("value"));
        return ResponseEntity.ok().build();
    }

    @DeleteMapping("/{key}")
    public ResponseEntity<Void> delete(@PathVariable String key) {
        promptService.delete(key);
        return ResponseEntity.noContent().build();
    }
}
