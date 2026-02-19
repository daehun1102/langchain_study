package com.ncs.backend.controller;

import com.ncs.backend.model.Document;
import com.ncs.backend.service.DocumentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    @PostMapping
    public ResponseEntity<Document> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "mainCategory", required = false) String mainCategory,
            @RequestParam(value = "subCategory", required = false) String subCategory
    ) throws IOException {
        Document doc = documentService.upload(file, mainCategory, subCategory);
        return ResponseEntity.ok(doc);
    }

    @GetMapping
    public ResponseEntity<List<Document>> findAll() {
        return ResponseEntity.ok(documentService.findAll());
    }

    @DeleteMapping("/{docId}")
    public ResponseEntity<Void> delete(@PathVariable String docId) {
        documentService.delete(docId);
        return ResponseEntity.noContent().build();
    }
}
