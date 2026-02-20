package com.ncs.backend.controller;

import com.ncs.backend.model.Document;
import com.ncs.backend.service.DocumentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    @PostMapping
    public ResponseEntity<?> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "mainCategory", required = false) String mainCategory,
            @RequestParam(value = "subCategory", required = false) String subCategory
    ) {
        try {
            Document doc = documentService.upload(file, mainCategory, subCategory);
            return ResponseEntity.ok(doc);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        } catch (IOException e) {
            return ResponseEntity.internalServerError().body(Map.of("error", "파일 저장 중 오류가 발생했습니다."));
        }
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
