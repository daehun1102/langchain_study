package com.ncs.backend.service;

import com.ncs.backend.mapper.DocumentMapper;
import com.ncs.backend.model.Document;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentMapper documentMapper;
    private final RestClient pythonRestClient;

    @Value("${app.upload-dir}")
    private String uploadDir;

    public Document upload(MultipartFile file, String mainCategory, String subCategory) throws IOException {
        // 파일 유효성 검사
        if (file.isEmpty()) {
            throw new IllegalArgumentException("업로드된 파일이 비어있습니다.");
        }
        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null || originalFilename.isBlank()) {
            throw new IllegalArgumentException("파일명이 없습니다.");
        }
        // Path Traversal 방지: 파일명 부분만 추출
        String filename = Paths.get(originalFilename).getFileName().toString();

        String docId = UUID.randomUUID().toString();

        Path uploadPath = Paths.get(uploadDir).toAbsolutePath();
        if (!Files.exists(uploadPath)) {
            Files.createDirectories(uploadPath);
        }
        Path filePath = uploadPath.resolve(docId + "_" + filename);
        file.transferTo(filePath);

        Document doc = new Document();
        doc.setDocId(docId);
        doc.setFilename(filename);
        doc.setMainCategory(mainCategory);
        doc.setSubCategory(subCategory);
        doc.setStatus("PENDING");
        documentMapper.insert(doc);

        // Python AI 서버에 벡터 저장 요청
        try {
            Map<String, String> ingestReq = Map.of(
                "doc_id", docId,
                "file_path", filePath.toAbsolutePath().toString()
            );
            Map<?, ?> response = pythonRestClient.post()
                    .uri("/internal/ingest")
                    .body(ingestReq)
                    .retrieve()
                    .body(Map.class);

            String status = response != null ? (String) response.get("status") : "FAILED";
            documentMapper.updateStatus(docId, status);
            doc.setStatus(status);
            log.info("[DocumentService] ingest 완료: docId={}, status={}", docId, status);
        } catch (Exception e) {
            log.error("[DocumentService] Python ingest 호출 실패: docId={}, error={}", docId, e.getMessage());
            documentMapper.updateStatus(docId, "FAILED");
            doc.setStatus("FAILED");
        }

        return doc;
    }

    public List<Document> findAll() {
        return documentMapper.findAll();
    }

    public void delete(String docId) throws IOException {
        // DB에서 파일 정보 조회 후 파일시스템에서도 삭제
        Document doc = documentMapper.findById(docId);
        if (doc != null) {
            Path uploadPath = Paths.get(uploadDir).toAbsolutePath();
            // uploads/{docId}_{filename} 패턴으로 저장된 파일 삭제
            Path filePath = uploadPath.resolve(docId + "_" + doc.getFilename());
            Files.deleteIfExists(filePath);
        }
        documentMapper.delete(docId);
    }

    public void updateStatus(String docId, String status) {
        documentMapper.updateStatus(docId, status);
    }

    public List<String> findDocIdsByCategory(String mainCategory, String subCategory) {
        return documentMapper.findDocIdsByCategory(mainCategory, subCategory);
    }
}
