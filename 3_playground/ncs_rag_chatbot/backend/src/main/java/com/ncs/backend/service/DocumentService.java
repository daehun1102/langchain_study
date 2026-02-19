package com.ncs.backend.service;

import com.ncs.backend.mapper.DocumentMapper;
import com.ncs.backend.model.Document;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentMapper documentMapper;

    @Value("${app.upload-dir}")
    private String uploadDir;

    public Document upload(MultipartFile file, String mainCategory, String subCategory) throws IOException {
        String docId = UUID.randomUUID().toString();

        Path uploadPath = Paths.get(uploadDir).toAbsolutePath();
        if (!Files.exists(uploadPath)) {
            Files.createDirectories(uploadPath);
        }
        String filename = file.getOriginalFilename();
        Path filePath = uploadPath.resolve(docId + "_" + filename);
        file.transferTo(filePath);

        Document doc = new Document();
        doc.setDocId(docId);
        doc.setFilename(filename);
        doc.setMainCategory(mainCategory);
        doc.setSubCategory(subCategory);
        doc.setStatus("PENDING");
        documentMapper.insert(doc);

        return doc;
    }

    public List<Document> findAll() {
        return documentMapper.findAll();
    }

    public void delete(String docId) {
        documentMapper.delete(docId);
    }

    public void updateStatus(String docId, String status) {
        documentMapper.updateStatus(docId, status);
    }

    public List<String> findDocIdsByCategory(String mainCategory, String subCategory) {
        return documentMapper.findDocIdsByCategory(mainCategory, subCategory);
    }
}
