package com.sdi.chatbot.service;

import com.sdi.chatbot.mapper.DocumentMapper;
import com.sdi.chatbot.model.Document;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentMapper documentMapper;
    private final RestClient aiRestClient;

    public List<Document> findAll() {
        return documentMapper.findAll();
    }

    public Document upload(MultipartFile file) throws Exception {
        String docId = UUID.randomUUID().toString();

        // AI 서버에 색인 요청
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new ByteArrayResource(file.getBytes()) {
            @Override public String getFilename() { return file.getOriginalFilename(); }
        });
        aiRestClient.post()
                .uri("/internal/ingest?doc_id=" + docId)
                .body(body)
                .retrieve()
                .toBodilessEntity();

        // DB 등록
        Document doc = new Document();
        doc.setDocId(docId);
        doc.setFilename(file.getOriginalFilename());
        doc.setDocType("txt");
        doc.setStatus("INDEXED");
        documentMapper.insert(doc);
        return doc;
    }

    public void delete(String docId) {
        aiRestClient.delete()
                .uri("/internal/delete/" + docId)
                .retrieve()
                .toBodilessEntity();
        documentMapper.deleteByDocId(docId);
    }
}
