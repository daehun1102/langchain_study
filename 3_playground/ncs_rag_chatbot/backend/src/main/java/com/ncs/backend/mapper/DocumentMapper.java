package com.ncs.backend.mapper;

import com.ncs.backend.model.Document;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import java.util.List;

@Mapper
public interface DocumentMapper {
    void insert(Document document);
    List<Document> findAll();
    Document findById(String docId);
    void updateStatus(@Param("docId") String docId, @Param("status") String status);
    void delete(String docId);
    List<String> findDocIdsByCategory(@Param("mainCategory") String mainCategory,
                                      @Param("subCategory") String subCategory);
}
