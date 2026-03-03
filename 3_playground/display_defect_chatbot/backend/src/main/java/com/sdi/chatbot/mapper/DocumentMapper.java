package com.sdi.chatbot.mapper;

import com.sdi.chatbot.model.Document;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

@Mapper
public interface DocumentMapper {
    List<Document> findAll();
    void insert(Document document);
    void deleteByDocId(String docId);
    void updateStatus(String docId, String status);
}
