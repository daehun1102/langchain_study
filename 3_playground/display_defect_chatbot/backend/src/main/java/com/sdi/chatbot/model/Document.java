package com.sdi.chatbot.model;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class Document {
    private String docId;
    private String filename;
    private String docType;
    private String status;
    private LocalDateTime createdAt;
}
