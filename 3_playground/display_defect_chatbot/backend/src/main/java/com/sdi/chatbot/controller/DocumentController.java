package com.sdi.chatbot.controller;

import com.sdi.chatbot.model.Document;
import com.sdi.chatbot.service.DocumentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    @GetMapping
    public ResponseEntity<List<Document>> list() {
        return ResponseEntity.ok(documentService.findAll());
    }

    @PostMapping
    public ResponseEntity<Document> upload(@RequestParam("file") MultipartFile file) throws Exception {
        return ResponseEntity.ok(documentService.upload(file));
    }

    @DeleteMapping("/{docId}")
    public ResponseEntity<Void> delete(@PathVariable String docId) {
        documentService.delete(docId);
        return ResponseEntity.noContent().build();
    }
}
